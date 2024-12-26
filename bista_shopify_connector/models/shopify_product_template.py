##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import pprint
from .. import shopify
import urllib.parse as urlparse
from odoo.exceptions import AccessError, ValidationError

from odoo import models, fields, api, _, tools
from odoo.tools.translate import html_translate
import logging
import time
import base64
import requests
_logger = logging.getLogger(__name__)


class ShopifyProductTemplate(models.Model):
    _name = 'shopify.product.template'
    _description = 'Shopify Product Template'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'product_tmpl_id'

    name = fields.Char("Name",
                       help="Enter Name",
                       tracking=True, copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        "Shopify Config",
                                        help="Enter Shopify Config",
                                        tracking=True,
                                        required=True, copy=False)
    body_html = fields.Html("Body Html",
                            help="Enter Body Html",
                            tracking=True,
                            translate=html_translate, copy=False)
    vendor = fields.Many2one("res.partner",
                             "Shopify Vendor",
                             help="Enter Vendor",
                             domain=[('supplier_rank', '>', 0)],
                             tracking=True, copy=False)

    product_type = fields.Many2one("product.category",
                                   "Shopify Product Type",
                                   help="Enter Shopify Product Type",
                                   tracking=True, copy=False)
    shopify_published = fields.Boolean(
        "Published in Shopify",
        help="Check if Shopify Published Product or not?",
        tracking=True,
        default=True, copy=False)
    shopify_published_scope = fields.Selection([('web', 'Web'), ('global', 'Global')],
        default='web',
        copy=False,
        help='Web: The product is published to the Online Store channel.\n \
              Global: The product is published to both the Online Store channel and the Point of Sale channel.')
    shopify_prod_tmpl_id = fields.Char(
        "Shopify Product Template ID",
        help="Enter Shopify Product Template ID",
        tracking=True,
        readonly=False, copy=False)
    product_tmpl_id = fields.Many2one(
        "product.template",
        "Product Template",
        help="Enter Product Template",
        required=True,
        tracking=True, copy=False)
    shopify_error_log = fields.Text(
        "Shopify Error",
        help="Error occurs while exporting move to the shopify",
        readonly=False, copy=False)
    r_prod_tags = fields.Many2many(related='product_tmpl_id.prod_tags_ids',
                                   string='Product Tags',
                                   tracking=True)
    r_prov_tags = fields.Many2many(related='product_tmpl_id.province_tags_ids',
                                   string='Province Tags',
                                   tracking=True)
    last_updated_date = fields.Datetime(string='Last Updated Date',
                                        readonly=False, copy=False)
    shopify_handle = fields.Char("Handle", copy=False)
    shopify_prod_collection_ids = fields.Many2many(
        'shopify.product.collection',
        'shopify_collection_product_template_rel',
        'collection_id',
        'prod_template_id',
        string='Collections'
    )

    def check_product_sync(self, sku, barcode, name, variant_id, sync_by):
        message = ""
        if sync_by == "sku" and not sku:
            message = "Product %s do not have SKU in shopify of variant id %s." % (name, variant_id)
        elif sync_by == "barcode" and not barcode:
            message = "Product %s do not have Barcode in shopify for variant id %s." % (name, variant_id)
        elif sync_by == "sku_or_barcode" and not sku and not barcode:
            message = "Product %s do not have SKU or Barcode in shopify for variant id %s." % (name, variant_id)
        return message

    # @api.model
    # def create(self, vals):
    #     """
    #     Prevent the user to create a shopify product template record with the
    #     same shopify config.
    #     """
    #     res = super(ShopifyProductTemplate, self).create(vals)
        # product_template_id = vals.get('product_tmpl_id')
        # if res.shopify_config_id and product_template_id:
        #     shopify_product_templates = self.search_count(
        #         [('id', '!=', res.id),
        #             ('product_tmpl_id', '=', product_template_id),
        #      ('shopify_config_id', '=', res.shopify_config_id.id)])
        #     if shopify_product_templates >= 1:
        #         raise ValidationError(
        #             _("You cannot create multiple records for same shopify "
        #               "configuration for template %s" % product_template_id))
        # create shopify product variant for this record
        # vals_list = []
        # for v_prod in self.env['product.product'].search(
        #         [('product_tmpl_id', '=', res.product_tmpl_id.id)]):
        #     vals_list.append(
        #         {
        #             'product_template_id': res.product_tmpl_id.id,
        #             'product_variant_id': v_prod.id,
        #             'lst_price': v_prod.lst_price,
        #             'shopify_product_template_id': res.id,
        #             'shopify_config_id': res.shopify_config_id.id,
        #             'shopify_published_variant': res.shopify_published,
        #         })
        # if vals_list:
        #     self.env['shopify.product.product'].sudo().create(vals_list)
        # return res

    # def write(self, vals):
    #     """
    #     Prevent the user to update a shopify product template record with the
    #     same shopify config.
    #     """
    #     res = super(ShopifyProductTemplate, self).write(vals)
    #     for rec in self:
    #         product_template_id = rec.product_tmpl_id.id
    #         shopify_config_id = rec.shopify_config_id
    #         if shopify_config_id:
    #             shopify_product_variants_count = self.search_count(
    #                 [('id', '!=', rec.id),
    #                     ('product_tmpl_id', '=', product_template_id),
    #                  ('shopify_config_id', '=', shopify_config_id.id)])
    #
    #             if shopify_product_variants_count >= 1:
    #                 raise ValidationError(
    #                     _("You cannot create multiple records for same shopify "
    #                       "configuration %s" % product_template_id))
    #     return res

    def fetch_all_shopify_products(self, shopify_config):
        """return: shopify products list"""
        try:
            shopify_product_list, page_info = [], False
            while 1:
                if shopify_config.last_product_import_date:
                    if page_info:
                        page_wise_product_list = shopify.Product().find(
                            limit=250, page_info=page_info)
                    else:
                        page_wise_product_list = shopify.Product().find(
                            updated_at_min=shopify_config.last_product_import_date,
                            limit=250)
                else:
                    if page_info:
                        page_wise_product_list = shopify.Product().find(
                            limit=250, page_info=page_info)
                    else:
                        page_wise_product_list = shopify.Product().find(limit=250)
                page_url = page_wise_product_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and \
                            parsed.get('page_info', False)[0] or False
                shopify_product_list += page_wise_product_list
                if not page_info:
                    break
            return shopify_product_list
        except Exception as e:
            raise AccessError(e)

    def shopify_import_product_by_ids(self, shopify_config,
                                      shopify_product_by_ids=False):
        shopify_config.check_connection()
        error_log_env = self.env['shopify.error.log']
        proudct_list = []
        shopify_log_line_dict = self.env.context.get('shopify_log_line_dict',
        {'error': [], 'success': []})
        if type(shopify_product_by_ids) != int:
            for product in ''.join(shopify_product_by_ids.split()).split(','):
                try:
                    proudct_list.append(shopify.Product().find(product))
                except:
                    raise ValidationError('Product Not Found! Please enter valid Product ID!')
        else:
            proudct_list.append(shopify.Product().find(shopify_product_by_ids))
        for shopify_product in proudct_list:
            shopify_product_dict = shopify_product.to_dict()
            shopify_product_template_id = self.create_update_shopify_product(
            shopify_product_dict, shopify_config)
        return shopify_product_template_id

    def update_shopify_product(self):
        shopify_config = self.shopify_config_id
        shopify_prod_tmpl_id = self.shopify_prod_tmpl_id
        if not shopify_config or not self.shopify_prod_tmpl_id:
            pass
        shopify_config.check_connection()
        error_log_env = self.env['shopify.error.log']
        shopify_log_line_dict = self.env.context.get('shopify_log_line_dict',
            {'error': [], 'success': []})
        shopify_log_id = error_log_env.create_update_log(
            shopify_config_id=shopify_config,
            operation_type='import_product')
        shop_product = shopify.Product().find(shopify_prod_tmpl_id)
        shopify_product_dict = shop_product.to_dict()
        shopify_product_template_id = self.with_context(
        shopify_log_line_dict=shopify_log_line_dict,
        shopify_log_id=shopify_log_id).create_update_shopify_product(
        shopify_product_dict, shopify_config)

        if not shopify_log_id.shop_error_log_line_ids and not self.env.context.get('shopify_log_id', False):
            shopify_log_id.unlink()
        return shopify_product_template_id

    def export_shopify(self):
        """
        This method is called by export button, it calls the export_product
        method on shopify config object.
        """
        for rec in self:
            if not rec.shopify_prod_tmpl_id:
                shopify_config_rec = rec.shopify_config_id
                shopify_config_rec.export_product(rec)

    def shopify_import_product(self, shopify_config):
        """This method is used to create queue and queue line for products"""
        shopify_config.check_connection()
        shopify_product_list = self.fetch_all_shopify_products(shopify_config)
        if shopify_product_list:
            for shopify_products in tools.split_every(250, shopify_product_list):
                shop_queue_id = shopify_config.action_create_queue(
                    'import_product')
                for product in shopify_products:
                    product_dict = product.to_dict()
                    name = product_dict.get('title', '') or ''
                    line_vals = {
                        'shopify_id': product_dict.get('id') or '',
                        'state': 'draft',
                        'name': name and name.strip(),
                        'record_data': pprint.pformat(product_dict),
                        'shopify_config_id': shopify_config.id,
                    }
                    shop_queue_id.action_create_queue_lines(line_vals)
        shopify_config.last_product_import_date = fields.Datetime.now()
        return True

    def odoo_product_search_sync(self, shopify_config_id, sku, barcode):
        sync_product = shopify_config_id.sync_product
        odoo_product = False
        domain_product = []
        if sync_product == 'sku' and sku:
            domain_product = [('default_code', '=', sku)]
        elif sync_product == 'barcode' and barcode:
            domain_product = [('barcode', '=', barcode)]
        elif sync_product == 'sku_barcode':
            domain_product = ['|', ('barcode', '=', barcode),
                              ('default_code', '=', sku)]
        if domain_product:
            odoo_product = self.env['product.product'].search(domain_product, limit=1)
        return odoo_product

    def shopify_product_search_sync(self, shopify_config_id, sku, barcode):
        sync_product = shopify_config_id.sync_product
        odoo_product = False
        domain_product = []
        if sync_product == 'sku' and sku:
            domain_product = [('default_code', '=', sku)]
        elif sync_product == 'barcode' and barcode:
            domain_product = [('barcode', '=', barcode)]
        elif sync_product == 'sku_barcode':
            domain_product = ['|', ('barcode', '=', barcode),
                              ('default_code', '=', sku)]
        if domain_product:
            odoo_product = self.env['shopify.product.product'].sudo().search(domain_product, limit=1)
        return odoo_product

    def create_variant_product(self, result, price, product_category,
                               is_service_product=False):
        """Fetch a product with variant from shopify"""
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        product_template_obj = self.env['product.template']
        template_title = result.get('title', '')

        attrib_line_vals = []
        for attrib in result.get('options'):
            attrib_name = attrib.get('name')
            attrib_values = attrib.get('values')
            attribute = product_attribute_obj.sudo().search(
                [('name', '=ilike', attrib_name)], limit=1)
            if not attribute:
                attribute = product_attribute_obj.sudo().create({'name': attrib_name})
            attr_val_ids = []

            for attrib_vals in attrib_values:
                attrib_value = product_attribute_value_obj.sudo().search(
                    [('attribute_id', '=', attribute.id),
                     ('name', '=', attrib_vals)], limit=1)
                if not attrib_value:
                    attrib_value = product_attribute_value_obj.sudo().with_context(
                        active_id=False).create(
                        {'attribute_id': attribute.id, 'name': attrib_vals})
                attr_val_ids.append(attrib_value.id)

            if attr_val_ids:
                attribute_line_ids_data = [0, False,
                                           {'attribute_id': attribute.id,
                                            'value_ids': [
                                                [6, False, attr_val_ids]]}]
                attrib_line_vals.append(attribute_line_ids_data)
        if attrib_line_vals:
            product_template = product_template_obj.create(
                {'name': template_title,
                 'type': 'product',
                 'attribute_line_ids': attrib_line_vals,
                 'description_sale': result.get('description', ''),
                 'categ_id': product_category and product_category.id or False,
                 'list_price': price,
                 'sale_ok': True,
                 'purchase_ok': True,
                 'weight': result.get('weight', ''),
                 })
            if is_service_product:
                product_template.update({
                    'type': 'service',
                    'invoice_policy': 'order'
                })
        return product_template

    def set_variant_data(self, result, product_template, shopify_prd_tmpl_id,
                         shopify_config_id):
        """ this method will use for set variant data in product template"""
        product_attribute_obj = self.env['product.attribute']
        product_attribt_val_obj = self.env['product.attribute.value']
        odoo_product_obj = self.env['product.product']
        for variation in result.get('variants'):
            sku = variation.get('sku')
            price = variation.get('price')
            barcode = variation.get('barcode') or False
            variant_id = variation.get('id')
            inventory_item_id = variation.get('inventory_item_id')
            if barcode and barcode.__eq__("false"):
                barcode = False
            attribute_value_ids = []
            variation_attributes = []
            option_name = []
            for options in result.get('options'):
                attrib_name = options.get('name')
                attrib_name and option_name.append(attrib_name)

            option1 = variation.get('option1', False)
            option2 = variation.get('option2', False)
            option3 = variation.get('option3', False)
            if option1 and (option_name and option_name[0]):
                variation_attributes.append(
                    {"name": option_name[0], "option": option1})
            if option2 and (option_name and option_name[1]):
                variation_attributes.append(
                    {"name": option_name[1], "option": option2})
            if option3 and (option_name and option_name[2]):
                variation_attributes.append(
                    {"name": option_name[2], "option": option3})

            for variation_attribute in variation_attributes:
                attribute_val = variation_attribute.get('option')
                attribute_name = variation_attribute.get('name')
                product_attribute = product_attribute_obj.search(
                    [('name', '=ilike', attribute_name)], limit=1)
                if product_attribute:
                    product_attribute_value = product_attribt_val_obj.search(
                        [('attribute_id', '=', product_attribute.id),
                         ('name', '=', attribute_val)], limit=1)
                    product_attribute_value and attribute_value_ids.append(
                        product_attribute_value.id)
            if attribute_value_ids:
                product_id = odoo_product_obj.search([('product_tmpl_id', '=',
                                          product_template.id)])
                pt_atribt_ids = product_id.product_template_attribute_value_ids
                attribute_ids = pt_atribt_ids.filtered(
                    lambda a:  a.product_attribute_value_id.id in
                               attribute_value_ids)
                odoo_product = product_id.filtered(
                    lambda a: a.product_template_attribute_value_ids ==
                              attribute_ids)
                if odoo_product:
                    odoo_product and odoo_product.write({'default_code': sku})
                # TODO: remove comment after update shopify product duplicate barcode
                # if barcode:
                #     odoo_product and odoo_product.write({'barcode': barcode})
                if price:
                    odoo_product and odoo_product.write({'list_price': price})
                # for shopify product variant
                if odoo_product:
                    odoo_product.write({'shopify_product_product_ids': [
                        (0, 0, {
                        'product_template_id': odoo_product.product_tmpl_id.id,
                        'shopify_config_id': shopify_config_id.id,
                        'shopify_product_id': variant_id,
                        'lst_price': price,
                        'shopify_inventory_item_id': inventory_item_id,
                        'shopify_product_template_id': shopify_prd_tmpl_id.id,
                        })]})

    def create_update_shopify_product(self, product_dict, shopify_config_id):
        """Fetch a product from shopify"""
        shopify_config_id.check_connection()
        error_log_env = self.env['shopify.error.log']
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        shopify_product_obj = self.env['shopify.product.product']
        product_template_obj = self.env['product.template']
        product_category_obj = self.env['product.category']
        partner_obj = self.env['res.partner']
        try:
            is_service_product = False
            tmpl_id = False
            template_title = product_dict.get('title')
            body_html = product_dict.get('body_html')
            tags = product_dict.get('tags')
            vendor = product_dict.get('vendor')
            handle = product_dict.get('handle')
            product_type = product_dict.get('product_type')
            shopify_tmpl_id = product_dict.get('id')
            shopify_published_scope = product_dict.get('published_scope')
            if product_type == 'Service':
                is_service_product = True
            shopify_template = self.search(
                [('shopify_prod_tmpl_id', '=', str(shopify_tmpl_id)),
                 ('shopify_config_id', '=', shopify_config_id.id)])
            if shopify_template:
                if len(shopify_template.product_tmpl_id.product_variant_ids.ids) != len(
                        product_dict.get('variants')):
                    template = str(template_title) + ':' + str(shopify_tmpl_id)
                    error_message = "Shopify Product not match with Odoo Product %s " % template
                    error_log_env.create_update_log(
                        shop_error_log_id=shop_error_log_id,
                        shopify_log_line_dict={'error': [
                            {'error_message': error_message,
                             'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            for variant in product_dict.get('variants'):
                odoo_product = False
                barcode = variant.get('barcode', '') or False
                weight = variant.get('weight')
                sku = variant.get('sku', '')
                title = variant.get('title')
                price = variant.get('price').replace(",", ".")
                variant_id = variant.get('id')
                inventory_item_id = variant.get('inventory_item_id')
                fulfillment_service = variant.get('fulfillment_service')
                if fulfillment_service == "gift_card":
                    is_service_product = True
                shopify_variant = shopify_product_obj.search(
                    [('product_variant_id', '=', variant_id),
                     ('shopify_config_id', '=', shopify_config_id.id)], limit=1)
                sync_product = shopify_config_id.sync_product
                error_msg = self.check_product_sync(sku, barcode, template_title, variant_id, sync_product)
                if error_msg:
                    error_log_env.create_update_log(
                        shop_error_log_id=shop_error_log_id,
                        shopify_config_id=shopify_config_id,
                        operation_type='import_product',
                        shopify_log_line_dict={'error': [
                            {'error_message': error_msg,
                             'queue_job_line_id': queue_line_id and queue_line_id.id or False,
                             'state': 'failed'}]})
                    # queue_line_id and queue_line_id.update({'state': 'failed'})
                    continue
                # assign All category
                if product_type.strip():
                    product_category = product_category_obj.search(
                        [('name', '=', product_type)], limit=1)
                    if not product_category:
                        product_category = product_category_obj.create(
                            {'name': product_type,
                             'property_cost_method': 'fifo',
                             'property_valuation': 'real_time',
                             })
                else:
                    product_category = self.env.ref(
                        'product.product_category_all')
                if not odoo_product and not shopify_variant:
                    # for product with variants
                    product_tmpl = self.search(
                        [('shopify_prod_tmpl_id', '=', str(shopify_tmpl_id)),
                         ('shopify_config_id', '=', shopify_config_id.id)],
                        limit=1)
                    if product_tmpl:
                        queue_line_id and queue_line_id.update({'state': 'processed',
                                              'product_id': product_tmpl.product_tmpl_id.id})
                        # continue
                    if vendor:
                        supplier = partner_obj.search([
                            ('name', '=', vendor),
                            ('supplier_rank', '>', 0),
                            ('company_id', '=',
                             shopify_config_id.default_company_id.id)], limit=1)
                    if len(product_dict.get('variants')) > 1 and \
                            title != 'Default Title':
                        odoo_product = self.odoo_product_search_sync(
                            shopify_config_id, sku, barcode)
                        # if not odoo_product:
                        #     error_message = "Facing a problems odoo product " \
                        #                     "sku: %s, barcode: %s" % (sku, barcode)
                        #     error_log_env.create_update_log(
                        #         shop_error_log_id=shop_error_log_id,
                        #         shopify_log_line_dict={
                        #             'error': [
                        #                 {'error_message': error_message,
                        #                     'queue_job_line_id': queue_line_id
                        #                                          and queue_line_id.id}]})
                        #     queue_line_id.update({'state': 'failed'})
                        product_tmpl_id = odoo_product and odoo_product.product_tmpl_id or False
                        if not product_tmpl_id and \
                                shopify_config_id.is_create_product:
                            # create product with variant
                            template_title = product_dict.get('title', '')
                            shopify_product = 0
                            if odoo_product:
                                shopify_product = shopify_product_obj.search_count(
                                    [('product_variant_id', '=', odoo_product.id),
                                    ('shopify_config_id', '=', shopify_config_id.id)])
                            if shopify_product >= 1:
                                error_message = "You cannot create multiple records for same shopify " \
                                       "configuration for product %s: %s" % (
                                       odoo_product.name, sku)
                                error_log_env.create_update_log(
                                    shop_error_log_id=shop_error_log_id,
                                    shopify_log_line_dict={'error': [
                                        {'error_message': error_message,
                                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                queue_line_id and queue_line_id.update({'state': 'failed'})
                            else:
                                # create product template
                                if shopify_config_id.is_create_product:
                                    product_tmpl_id = self.create_variant_product(
                                        product_dict, price, product_category,
                                        is_service_product)
                                else:
                                    error_message = "Odoo product not created for %s.\n" \
                                                    "if you want auto created it. enable it from shopify configuration" % (
                                                        template_title)
                                    error_log_env.create_update_log(
                                        shop_error_log_id=shop_error_log_id,
                                        shopify_log_line_dict={'error': [
                                            {'error_message': error_message,
                                             'queue_job_line_id': queue_line_id and queue_line_id.id}]})
                                    queue_line_id and queue_line_id.update(
                                        {'state': 'failed'})
                                    continue
                        tmpl_id = product_tmpl_id
                        if not tmpl_id:
                            error_message = "Odoo product not created for %s.\n" \
                                            "if you want auto created it. enable it from shopify configuration" % (
                                                template_title)
                            error_log_env.create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={'error': [
                                    {'error_message': error_message,
                                     'queue_job_line_id': queue_line_id and queue_line_id.id}]})
                            queue_line_id and queue_line_id.update(
                                {'state': 'failed'})
                            continue
                        # for shopify product template
                        shopify_prd_tmpl_id = self.search(
                            [('shopify_prod_tmpl_id', '=', str(shopify_tmpl_id))])
                        # TODO: collection (New API doesnot support it. So need to do R&D based on collection API)
                        shopify_product_templates = self.search_count(
                            [('product_tmpl_id', '=', product_tmpl_id.id),
                             ('shopify_config_id', '=', shopify_config_id.id)])
                        if not shopify_prd_tmpl_id:
                            shopify_tmpl_vals = {
                                'product_tmpl_id': product_tmpl_id.id,
                                'shopify_config_id': shopify_config_id.id,
                                'product_type': product_tmpl_id.categ_id.id,
                                'shopify_prod_tmpl_id': shopify_tmpl_id,
                                'body_html': body_html,
                                'shopify_published': True,
                                'shopify_published_scope': shopify_published_scope,
                                'shopify_handle': handle,
                            }
                            if supplier:
                                shopify_tmpl_vals.update({
                                    'vendor': supplier.id})

                            if shopify_product_templates >= 1:
                                error_message = "You cannot create multiple records for " \
                                    "same shopify configuration for product %s: %s" % (
                                       product_tmpl_id.name, sku)
                                error_log_env.create_update_log(
                                    shop_error_log_id=shop_error_log_id,
                                    shopify_log_line_dict={'error': [
                                        {'error_message': error_message,
                                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                queue_line_id and queue_line_id.update({'state': 'failed'})
                            else:
                                shopify_prd_tmpl_id = self.create(
                                    shopify_tmpl_vals)
                            # for set product variant data
                            try:
                                self.set_variant_data(product_dict,
                                                      product_tmpl_id,
                                                      shopify_prd_tmpl_id,
                                                      shopify_config_id)
                            except Exception as e:
                                error_message = "Facing a problems set product " \
                                          "variant data on product %s : %s" % (
                                            e, product_tmpl_id.name)
                                error_log_env.create_update_log(
                                    shop_error_log_id=shop_error_log_id,
                                    shopify_log_line_dict={'error': [
                                        {'error_message': error_message,
                                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                queue_line_id and queue_line_id.update({'state': 'failed'})
                            # for images
                            if product_tmpl_id and shopify_tmpl_id and not \
                                    shopify_product_templates >= 1 and shopify_config_id.is_sync_product_image:
                                self.sync_shopify_product_images(product_tmpl_id,
                                                                 shopify_tmpl_id)
                    # for product without variants
                    else:
                        odoo_product = self.odoo_product_search_sync(
                            shopify_config_id, sku, barcode)
                        if not odoo_product and sync_product == 'sku' and not sku or sync_product == 'barcode' and not barcode:
                            error_message = "Odoo product not found for sku: %s or barcode: %s" % (sku, barcode)
                            error_log_env.create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={
                                    'error': [
                                        {'error_message': error_message,
                                            'queue_job_line_id': queue_line_id
                                                                 and queue_line_id.id}]})
                            queue_line_id and queue_line_id.update({'state': 'failed'})
                            continue
                        tmpl_id = odoo_product and odoo_product.product_tmpl_id
                        if not tmpl_id:
                            temp_vals = {
                                'name': template_title,
                                'sale_ok': True,
                                'purchase_ok': True,
                                'published_on_shopify': True,
                                'description': body_html,
                                'default_code': sku or '',
                                'barcode': barcode or '',
                                'type': 'product',
                                'categ_id': product_category and
                                            product_category.id or False,
                                'list_price': price,
                                'weight': weight,
                            }
                            # set the service type and invoicing policy
                            if is_service_product:
                                temp_vals.update({
                                    'type': 'service',
                                    'invoice_policy': 'order'
                                })
                            # for set vendor
                            if supplier:
                                temp_vals.update({
                                    'seller_ids': [(4, supplier.id)]})
                            # for shopify tags
                            shopify_tag_obj = self.env['shopify.product.tags']
                            list_of_tags = []
                            for tag in tags.split(','):
                                if not len(tag) > 0 or tag == 'Default Title':
                                    continue
                                shopify_tag = shopify_tag_obj.search(
                                    [('name', '=', tag)], limit=1)
                                if not shopify_tag:
                                    shopify_tag = shopify_tag_obj.create(
                                        {'name': tag,
                                         'shopify_config_ids': [(4, shopify_config_id.id)]})
                                list_of_tags.append(shopify_tag.id)
                            temp_vals.update(
                                {'prod_tags_ids': [(6, 0, list_of_tags)]})
                            # create product template
                            if shopify_config_id.is_create_product:
                                tmpl_id = product_template_obj.create(temp_vals)
                            else:
                                error_message = "Odoo product not created for %s.\n" \
                                                "if you want auto created it. enable it from shopify configuration" % (
                                                    template_title)
                                error_log_env.create_update_log(
                                    shop_error_log_id=shop_error_log_id,
                                    shopify_log_line_dict={'error': [
                                        {'error_message': error_message,
                                         'queue_job_line_id': queue_line_id and queue_line_id.id}]})
                                queue_line_id and queue_line_id.update(
                                    {'state': 'failed'})
                                continue
                        # for shopify product template
                        shopify_prd_tmpl_id = self.search(
                            [('shopify_prod_tmpl_id', '=',
                              str(shopify_tmpl_id)),
                             ('shopify_config_id', '=', shopify_config_id.id)])

                        # TODO: collection (New API doesnot support it. So need to do R&D based on collection API)

                        shopify_tmpl_vals = {
                            'product_tmpl_id': tmpl_id.id,
                            'shopify_config_id': shopify_config_id.id,
                            'product_type': tmpl_id.categ_id.id,
                            'shopify_prod_tmpl_id': shopify_tmpl_id,
                            'body_html': body_html,
                            'shopify_published': True,
                            'shopify_published_scope': shopify_published_scope,
                            'shopify_handle': handle,
                        }
                        if supplier:
                            shopify_tmpl_vals.update({'vendor': supplier.id})
                        shopify_product_templates = self.search_count(
                            [('product_tmpl_id', '=', tmpl_id.id),
                             ('shopify_config_id', '=', shopify_config_id.id)])
                        if shopify_product_templates > 1:
                            error_message = "You cannot create multiple records for same " \
                                "shopify configuration for product %s: %s" % (
                                   tmpl_id.name, sku)
                            error_log_env.create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={'error': [
                                    {'error_message': error_message,
                                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                            queue_line_id and queue_line_id.update({'state': 'failed',
                                                  'product_id': tmpl_id and tmpl_id.id,
                                                })
                        if shopify_prd_tmpl_id:
                            shopify_prd_tmpl_id.update(shopify_tmpl_vals)
                        else:
                            shopify_prd_tmpl_id = self.create(shopify_tmpl_vals)
                        # for shopify product variant
                        s_prd_id = shopify_product_obj.search([
                            ('shopify_product_id', '=', variant.get('id')),
                            ('shopify_config_id', '=', shopify_config_id.id)])
                        odoo_product = self.odoo_product_search_sync(
                            shopify_config_id, sku, barcode)
                        if not odoo_product:
                            error_message = "Odoo product not found for sku: %s or barcode: %s" % (sku, barcode)
                            error_log_env.create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={
                                    'error': [
                                        {'error_message': error_message,
                                            'queue_job_line_id': queue_line_id
                                                                 and queue_line_id.id}]})
                            queue_line_id and queue_line_id.update({'state': 'failed',
                                                  'product_id': tmpl_id and tmpl_id.id,
                                                })
                            continue
                        s_prd_vals = {
                            'product_variant_id': odoo_product.id,
                            'product_template_id': tmpl_id.id,
                            'shopify_config_id': shopify_config_id.id,
                            'shopify_product_id': variant.get('id'),
                            'lst_price': price,
                            'shopify_inventory_item_id': inventory_item_id,
                            'shopify_product_template_id':
                                shopify_prd_tmpl_id.id,
                        }
                        if not s_prd_id:
                            shopify_product_obj.create(s_prd_vals)
                        else:
                            s_prd_id.update(s_prd_vals)
                        # for images
                        if tmpl_id and shopify_tmpl_id and \
                                shopify_config_id.is_sync_product_image:
                            self.sync_shopify_product_images(tmpl_id,
                                                             shopify_tmpl_id)
                        shopify_product = shopify_product_obj.search_count(
                            [('product_template_id', '=', tmpl_id.id),
                             ('product_variant_id', '=', odoo_product.id),
                             ('shopify_config_id', '=', shopify_config_id.id)])
                        if shopify_product > 1:
                            error_message = "You cannot create multiple records for same shopify " \
                                            "configuration for product %s: %s" % (
                                                odoo_product.name, sku)
                            error_log_env.create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={'error': [
                                    {'error_message': error_message,
                                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                    if queue_line_id:
                        queue_line_id and queue_line_id.update({'state': 'processed',
                                              'product_id': tmpl_id and tmpl_id.id})
        except Exception as e:
            error_message = "Facing a problem while importing Product!: %s" % e
            error_log_env.create_update_log(
                shop_error_log_id=shop_error_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': error_message,
                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.update({'state': 'failed'})

    def sync_shopify_product_images(self, product_tmpl_id=False,
                                    shopify_tmpl_id=False):
        shopify_product_obj = self.env['shopify.product.product']
        shopify_product_img_obj = self.env['product.multi.images']
        get_images = shopify.Image.find(product_id=str(shopify_tmpl_id))
        for image in get_images:
            image_data = image.attributes
            url = image_data.get('src')
            if not url:
                continue
            shopify_image_id = image_data.get('id')
            image = base64.b64encode(
                requests.get(url.strip()).content).replace(b'\n', b'')
            if image_data.get('position') == 1:
                shopify_gallery_image = shopify_product_img_obj.sudo().search(
                    [('product_template_id', '=', product_tmpl_id.id),
                     ('shopify_image_id', '=', shopify_image_id)], limit=1)
                if shopify_gallery_image:
                    continue
                product_tmpl_id.write({'image_1920': image})
            if not image_data.get('variant_ids') and image_data.get(
                    'position') != 1:
                shopify_gallery_image = shopify_product_img_obj.search(
                    [('product_template_id', '=', product_tmpl_id.id),
                     ('shopify_image_id', '=', shopify_image_id)], limit=1)
                if shopify_gallery_image:
                    continue
                product_tmpl_id.write({'product_multi_images': [
                    (0, 0, {'image': image,
                            'description': product_tmpl_id.name,
                            'shopify_image_id': shopify_image_id})]})
            if image_data.get('variant_ids'):
                variant_id = image_data.get('variant_ids')[0]
                var_id = shopify_product_obj.search(
                    [('shopify_product_id', '=', variant_id)])
                var_id.product_variant_id.write({'image_1920': image})

    def fetch_all_shopify_inventory_level(self, shopify_config, shopify_location_ids):
        try:
            shopify_inventory_level_list, page_info = [], False
            while 1:
                if shopify_config.last_stock_import_date:
                    if page_info:
                        page_wise_inventory_list = shopify.InventoryLevel().find(page_info=page_info)
                    else:
                        page_wise_inventory_list = shopify.InventoryLevel().find(updated_at_min=shopify_config.last_stock_import_date, location_ids=','.join(shopify_location_ids))
                else:
                    if page_info:
                        page_wise_inventory_list = shopify.InventoryLevel().find(page_info=page_info)
                    else:
                        page_wise_inventory_list = shopify.InventoryLevel().find(location_ids=','.join(shopify_location_ids))
                page_url = page_wise_inventory_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and parsed.get('page_info', False)[0] or False
                shopify_inventory_level_list += page_wise_inventory_list
                if not page_info:
                    break
            return shopify_inventory_level_list
        except Exception as e:
            raise AccessError(e)

    def prepare_location_wise_inventory_level(self, shopify_inventory_levels):
        location_wise_inventory_dict = {}
        for inventory_level in shopify_inventory_levels:
            inventory_level = inventory_level.to_dict()
            shopify_location_id = inventory_level.get('location_id')
            if shopify_location_id in location_wise_inventory_dict:
                location_wise_inventory_dict[shopify_location_id].append(inventory_level)
            else:
                location_wise_inventory_dict.update({shopify_location_id: [inventory_level]})
        return location_wise_inventory_dict

    def prepare_inv_adjustment_lines(self, inventory_level_list, shopify_config, shopify_location_id):
        product_variant_ids, inventory_line_list = self.env['product.product'], []
        for inventory_level in inventory_level_list:
            shopify_inventory_item_id = inventory_level.get('inventory_item_id')
            qty = inventory_level.get('available', 0) or 0
            shopify_product = self.env['shopify.product.product'].search(
                [('product_variant_id.type', '!=', 'service'),
                 # ('product_variant_id.tracking', '=', 'none'),
                 ('update_shopify_inv', '=', True),
                 ('shopify_inventory_item_id', '=', shopify_inventory_item_id),
                 ('shopify_config_id', '=', shopify_config.id)], limit=1)
            if shopify_product:
                odoo_product_id = shopify_product.product_variant_id
                # if not any([line[2].get('product_id') == odoo_product_id.id for line in inventory_line_list]):
                if not any([line.get('product_id') == odoo_product_id.id for line in inventory_line_list]):
                    product_variant_ids += odoo_product_id
                    location_id = self.env['stock.location'].search(
                        [('shopify_config_id', '=', shopify_config.id),
                         ('usage', '=', 'internal'),
                         ('shopify_location_id', '=', shopify_location_id)],
                        limit=1)
                    # inventory_line_list.append((0, 0, {"product_id": odoo_product_id.id,
                    #                                    "location_id": location_id.id,
                    #                                    "product_qty": qty if qty > 0 else 0}))
                    inventory_line_list.append({"product_id": odoo_product_id.id,
                                                "location_id": location_id.id,
                                                "inventory_quantity": qty if qty > 0 else 0})
        return inventory_line_list, product_variant_ids

    # def create_process_inventory_adjustment(self, shopify_config, shopify_location_id, location_ids, inventory_line_list, product_variant_ids):
    #     shopify_location_id = self.env['stock.location'].search(
    #         [('shopify_config_id', '=', shopify_config.id),
    #          ('usage', '=', 'internal'),
    #          ('shopify_location_id', '=', shopify_location_id)], limit=1)
    #     inventory_adjustment_vals = {
    #         'shopify_adjustment': True,
    #         'location_ids': location_ids.ids,
    #         'name': 'SHOPIFY({}): Inventory for Account {} And Location {}'.format(fields.Date.to_string(fields.Date.today()), shopify_config.name, shopify_location_id.complete_name)}
    #     if inventory_adjustment_vals and inventory_line_list:
    #         locations = []
    #         for k, v, data in inventory_line_list:
    #             locations.append(data.get('location_id'))
    #         if len(locations) > 0:
    #             inventory_adjustment_vals.update({'location_ids': [(6, 0, locations)]})
    #         inventory_adjustment_vals.update({'line_ids': inventory_line_list,
    #                                           'product_ids': [(6, 0, product_variant_ids.ids)]})
    #         inventory_adjustment_id = self.env['stock.inventory'].create(inventory_adjustment_vals)
    #         inventory_adjustment_id.action_start()
    #         if shopify_config.is_validate_inv_adj:
    #             inventory_adjustment_id.action_validate()
    #         return inventory_adjustment_id
    #     return False
    
    def create_process_inventory_adjustment(self, shopify_config, inventory_line_list):
        Quant = self.env['stock.quant'].sudo().with_context(inventory_mode=True)
        # Commented to avoid recurring live sync from odoo to shopify when set to False.
        # When this boolean is False, User will have to manually click on 'Apply' button in stock quants and
        # this will update stock on shopify through live sync feature
        # validate_inv = shopify_config.is_validate_inv_adj
        for vals in inventory_line_list:
            quant_id = Quant.sudo().create(vals)
            # if validate_inv:
            #     quant_id.with_context(shopify_adjustment=True).action_apply_inventory()
            quant_id.with_context(shopify_adjustment=True).action_apply_inventory()
        return False

    # def cancel_existing_inventory_adjustments(self):
    #     inventory_adjuts_obj = self.env['stock.inventory']
    #     for inv in inventory_adjuts_obj.search([('shopify_adjustment', '=', True),
    #                                             ('state', '!=', 'done')]):
    #         if not inv.state == 'cancel':
    #             inv.action_cancel_draft()
    #             inv.write({'state': 'cancel'})

    def shopify_import_stock(self, shopify_config):
        error_log_env = self.env['shopify.error.log']
        shopify_log_id = error_log_env.create_update_log(
            shopify_config_id=shopify_config,
            operation_type='import_stock')
        shopify_product_template_ids = self.search(
            [('shopify_config_id', '=', shopify_config.id)])
        # self.cancel_existing_inventory_adjustments()
        if shopify_product_template_ids:
            shopify_config.check_connection()
            location_ids = self.env['stock.location'].search(
                [('shopify_config_id', '=', shopify_config.id),
                 ('shopify_location_id', '!=', False)])
            shopify_location_ids = location_ids.mapped('shopify_location_id')
            shopify_inventory_levels = self.fetch_all_shopify_inventory_level(
                shopify_config, shopify_location_ids)
            location_wise_inventory_dict = self.prepare_location_wise_inventory_level(
                shopify_inventory_levels)
            for shopify_location_id, inventory_level_list in location_wise_inventory_dict.items():
                try:
                    inventory_line_list, product_variant_ids = self.prepare_inv_adjustment_lines(
                        inventory_level_list, shopify_config, shopify_location_id)
                    inventory_adjustment_id = self.create_process_inventory_adjustment(
                        shopify_config, inventory_line_list)
                    # if inventory_adjustment_id:
                    #     log_message = "Imported Stock Successfully. Review Inventory Adjustment: %s" % (
                    #         inventory_adjustment_id.name)
                    #     error_log_env.create_update_log(
                    #         shop_error_log_id=shopify_log_id,
                    #         shopify_log_line_dict={
                    #             'error': [{'error_message': log_message}]})
                except Exception as e:
                    log_message = "Facing a problem while importing Stock: %s" %(e)
                    error_log_env.create_update_log(
                        shop_error_log_id=shopify_log_id,
                        shopify_log_line_dict={
                            'error': [{'error_message': log_message}]})
                    return False
            if not shopify_log_id.shop_error_log_line_ids:
                shopify_log_id.unlink()
            shopify_config.last_stock_import_date = fields.Datetime.now()
        return True
