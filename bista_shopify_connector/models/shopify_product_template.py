##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from .. import shopify
import urllib.parse as urlparse
from odoo.exceptions import AccessError, ValidationError

from odoo import models, fields, api, _, tools, registry
from odoo.tools.translate import html_translate
import logging
import base64
import traceback
import requests
from datetime import datetime, timedelta

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
                            help="Enter Body Html", translate=html_translate, copy=False)
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
        readonly=True, copy=False)
    product_tmpl_id = fields.Many2one(
        "product.template",
        "Product Template",
        help="Enter Product Template",
        required=True,
        tracking=True, copy=False)
    shopify_error_log = fields.Text(
        "Shopify Error",
        help="Error occurs while exporting move to the shopify",
        readonly=True, copy=False)
    r_prod_tags = fields.Many2many(related='product_tmpl_id.prod_tags_ids',
                                   string='Product Tags',
                                   tracking=True)
    r_prov_tags = fields.Many2many(related='product_tmpl_id.province_tags_ids',
                                   string='Province Tags',
                                   tracking=True)
    last_updated_date = fields.Datetime(string='Last Updated Date',
                                        readonly=True, copy=False)
    shopify_handle = fields.Char("Handle", copy=False)
    shopify_prod_collection_ids = fields.Many2many(
        'shopify.product.collection',
        'shopify_collection_product_template_rel',
        'collection_id',
        'prod_template_id',
        string='Collections'
    )
    ready_to_update = fields.Boolean(string="Ready to Update on Shopify",
                                     copy=False)
    company_id = fields.Many2one('res.company', string="Company")

    @api.onchange('shopify_config_id')
    def _onchange_shopify_config_id(self):
        if self.shopify_config_id:
            self.company_id = (self.shopify_config_id.default_company_id and
                               self.shopify_config_id.default_company_id.id or False)

    def create_update_shopify_product_from_webhook(self, res, shopify_config):
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Webhook Create/Update Product",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_product',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            shopify_config.check_connection()
            name = res.get('title', '')
            job_descr = _("WebHook Create/Update Product:   %s") % (
                    name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': res.get('id') or '',
                'operation_type': 'import_product',
                'parent_id': parent_log_line_id.id
            })
            user = self.env.ref('base.user_root')
            self.env["shopify.product.template"].with_user(user).with_company(shopify_config.default_company_id).with_delay(
                description=job_descr, max_retries=5).create_update_shopify_product(
                res, shopify_config, log_line_id)
            _logger.info("Started Process Of Creating Products Via Webhook->:")
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def open_shopify_product_variant(self):
        variant_ids = self.env['shopify.product.product'].search([(
            'shopify_product_template_id', '=', self.id)])
        if not variant_ids:
            raise ValidationError(_('No shopify product variants were found!'))
        return {
            'name': _('Shopify Variants'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'shopify.product.product',
            'context': self.env.context,
            'domain': [('id', 'in', variant_ids and variant_ids.ids or [])]
        }

    def check_product_sync(self, sku, barcode, name, variant_id, sync_by):
        message = ""
        if sync_by == "sku" and not sku:
            message = "Product %s do not have SKU in shopify of variant id %s." % (
                name, variant_id)
        elif sync_by == "barcode" and not barcode:
            message = "Product %s do not have Barcode in shopify for variant id %s." % (
                name, variant_id)
        elif sync_by == "sku_or_barcode" and not sku and not barcode:
            message = "Product %s do not have SKU or Barcode in shopify for variant id %s." % (
                name, variant_id)
        return message

    # @api.model
    # def create(self, vals):
    #     """
    #     Prevent the user to create a shopify product template record with the
    #     same shopify config.
    #     """
    #     res = super(ShopifyProductTemplate, self).create(vals)
    #     product_tmpl_id = self.env['product.template'].browse(
    #         vals.get('product_tmpl_id'))
    #     shopify_config_id = self.env['shopify.config'].browse(
    #         vals.get('shopify_config_id'))
    #     if shopify_config_id:
    #         product_tmpl_id.write(
    #             {'categ_id': shopify_config_id.product_categ_id.id})
    #     return res

    def fetch_all_shopify_products(self, shopify_config):
        """return: shopify products list"""
        try:
            shopify_product_list, page_info = [], False
            while 1:
                last_product_import_date, parameter_id = shopify_config.get_update_value_from_config(
                    operation='read', field='last_product_import_date', shopify_config_id=shopify_config,
                    field_value='')

                if last_product_import_date:
                    if page_info:
                        page_wise_product_list = shopify.Product().find(
                            limit=250, page_info=page_info)
                    else:
                        page_wise_product_list = shopify.Product().find(
                            updated_at_min=last_product_import_date or fields.Datetime.now(),
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

    def shopify_import_product_by_ids_with_queue(self, shopify_config,
                                                 shopify_product_by_ids=False):

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Products",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_product',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_config.check_connection()
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            proudct_list = []
            if type(shopify_product_by_ids) != int:
                for product in ''.join(shopify_product_by_ids.split()).split(','):
                    try:
                        proudct_list.append(shopify.Product().find(product))
                    except:
                        raise ValidationError(
                            'Product Not Found! Please enter valid Product ID!')
            else:
                proudct_list.append(shopify.Product().find(shopify_product_by_ids))
            seconds = 30
            for shopify_product in proudct_list:
                shopify_product_dict = shopify_product.to_dict()
                eta = datetime.now() + timedelta(seconds=seconds)
                name = shopify_product_dict.get('title', '') or ''
                job_descr = _("Create/Update Product:   %s") % (
                        name and name.strip())
                log_line_vals.update({
                    'name': job_descr,
                    'id_shopify': shopify_product_dict.get('id') or '',
                    'parent_id': parent_log_line_id.id
                })
                log_line_id = shopify_log_line_obj.create(log_line_vals)

                shopify_product_template_id = self_cr.with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5,
                    eta=eta).create_update_shopify_product(
                    shopify_product_dict, shopify_config, log_line_id)
                seconds += 2
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            cr.commit()
            return shopify_product_template_id
        except Exception as e:
            cr.rollback()
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def shopify_import_product_by_ids(self, shopify_config,
                                      shopify_product_by_ids=False):

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Product",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_product',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        try:
            shopify_config.check_connection()
            shopify_log_line_obj = self.env['shopify.log.line']
            proudct_list = []
            if type(shopify_product_by_ids) != int:
                for product in ''.join(shopify_product_by_ids.split()).split(','):
                    try:
                        proudct_list.append(shopify.Product().find(product))
                    except:
                        raise ValidationError(
                            'Product Not Found! Please enter valid Product ID!')
            else:
                proudct_list.append(shopify.Product().find(shopify_product_by_ids))
            for shopify_product in proudct_list:
                shopify_product_dict = shopify_product.to_dict()
                name = shopify_product_dict.get('title', '') or ''
                job_descr = _("Create/Update Product:   %s") % (
                        name and name.strip())
                log_line_id = shopify_log_line_obj.create({
                    'name': job_descr,
                    'shopify_config_id': shopify_config.id,
                    'id_shopify': shopify_product_dict.get('id') or '',
                    'operation_type': 'import_product',
                    'parent_id': parent_log_line_id.id,
                })
                shopify_product_template_id = self.create_update_shopify_product(
                    shopify_product_dict, shopify_config, log_line_id)
                parent_log_line_id.update({
                    'state': 'success',
                    'message': 'Operation Successful'
                })
                return shopify_product_template_id
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': traceback.format_exc(),
            })
            raise ValidationError(_(e))

    def import_template_to_odoo_btn(self):
        '''button method from product template form view to update product
        from shopify to odoo'''
        seconds = 5
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {}
        for product in self:
            log_line_vals.update({
                'shopify_config_id': product.shopify_config_id.id,
                'name': "Import products",
                'operation_type': 'import_product',
            })
            parent_log_line_id = shopify_log_line_obj.create(
                log_line_vals)
            eta = datetime.now() + timedelta(seconds=seconds)
            product.with_company( product.shopify_config_id.default_company_id).with_delay(
                description="Import Product", max_retries=5,
                eta=eta).update_shopify_product(parent_log_line_id)

    def export_template_to_shopify_btn(self):
        self.env['update.shopify.product'].with_context(export_product_template_info=True).update_shopify_product_template(self)

    def update_shopify_product(self, parent_log_line_id):
        try:
            shopify_config = self.shopify_config_id
            shopify_prod_tmpl_id = self.shopify_prod_tmpl_id
            shopify_log_line_obj = self.env['shopify.log.line']
            if not shopify_config or not self.shopify_prod_tmpl_id:
                pass
            shopify_config.check_connection()
            shop_product = shopify.Product().find(shopify_prod_tmpl_id)
            shopify_product_dict = shop_product.to_dict()
            seconds = 5
            eta = datetime.now() + timedelta(seconds=seconds)
            name = shopify_product_dict.get('title', '') or ''
            job_descr = _("Create/Update Product:   %s") % (
                    name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': shopify_product_dict.get('id') or '',
                'operation_type': 'import_product',
                'parent_id': parent_log_line_id.id
            })
            shopify_product_template_id = self.with_company(shopify_config.default_company_id).with_delay(
                description=job_descr, max_retries=5,
                eta=eta).create_update_shopify_product(
                shopify_product_dict, shopify_config, log_line_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            return shopify_product_template_id
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def write(self, vals):
        ready_to_update = False
        if not self._context.get('job_uuid'):
            if 'vendor' in vals:
                ready_to_update = True
            if 'shopify_prod_collection_ids' in vals:
                ready_to_update = True
        if ready_to_update:
            vals.update({'ready_to_update': ready_to_update})
        return super(ShopifyProductTemplate, self).write(vals)

    def update_product_shopify(self, parent_log_line_id):
        try:
            shopify_config = self.shopify_config_id
            shopify_prod_tmpl_id = self.shopify_prod_tmpl_id
            shopify_log_line_obj = self.env['shopify.log.line']
            if not shopify_config or not self.shopify_prod_tmpl_id:
                pass
            shopify_config.check_connection()
            shop_product = shopify.Product().find(shopify_prod_tmpl_id)
            shopify_product_dict = shop_product.to_dict()
            seconds = 5
            eta = datetime.now() + timedelta(seconds=seconds)
            name = shopify_product_dict.get('title', '') or ''
            job_descr = _("Update Product Template: %s") % (name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': shopify_product_dict.get('id') or '',
                'operation_type': 'update_product',
                'parent_id': parent_log_line_id.id
            })
            shopify_product_template_id = self.with_company(shopify_config.default_company_id).with_delay(
                description=job_descr, max_retries=5,
                eta=eta).update_product_to_shopify(shopify_config, log_line_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            return shopify_product_template_id
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def update_product_to_shopify(self, shopify_config, log_line_id):
        '''Function to update product information to shopify'''
        try:
            shopify_config.check_connection()
            shopify_product = shopify.Product().find(self.shopify_prod_tmpl_id)
            shopify_product.title = self.product_tmpl_id.name
            # new_product.published = s_product_tmpl_id.shopify_published
            # shopify_product.published_scope = self.shopify_published_scope
            if self.product_type:
                shopify_product.product_type = self.product_type.name
            if self.vendor:
                shopify_product.vendor = self.vendor.name

            str_prod_province_tags = []
            for prod_tag in self.product_tmpl_id.prod_tags_ids:
                str_prod_province_tags.append(prod_tag.name)
            for prov_tag in self.product_tmpl_id.province_tags_ids:
                str_prod_province_tags.append(prov_tag.name)
            tags = ",".join(str_prod_province_tags)
            if tags:
                shopify_product.tags = tags

            if self.body_html:
                shopify_product.body_html = str(self.body_html)
            else:
                shopify_product.body_html = ''

            for collection in self.shopify_prod_collection_ids:
                if collection.type == 'manual':
                    shopify_collection = shopify.CustomCollection().find(
                        collection.shopify_id)
                    if shopify_collection:
                        product_list = [prod.to_dict().get('id') for prod in
                                        shopify_collection.products() if
                                        str(prod.to_dict().get('id')) ==
                                        self.shopify_prod_tmpl_id]
                        if not product_list:
                            shopify_collection.add_product(shopify_product)
            success = shopify_product.save()
            self.ready_to_update = False
            variant_ids = self.env['shopify.product.product'].search([(
                'shopify_product_template_id', '=', self.id), ('variant_ready_for_update', '=', True)])
            if variant_ids:
                self.env['update.shopify.variant'].update_shopify_product_variant(variant_ids)
                variant_ids.write({
                    'variant_ready_for_update': False
                })
            log_line_id.sudo().write({
                'state': 'success',
                'related_model_name': 'product.product',
                'related_model_id': ",".join([str(id) for id in self.product_tmpl_id.product_variant_ids.ids]),
            })
        except Exception as e:
            error_message = ("Facing a problem while updating Product to "
                             "shopify !: %s" % e)
            log_line_id.sudo().write({
                'state': 'error',
                'message': error_message
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def export_shopify(self):
        """
        This method is called by export button, it calls the export_product
        method on shopify config object.
        """
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Export Products",
            'operation_type': 'export_product',
        }
        parent_log_line_id = False
        shopify_initial_id = False
        for rec in self:
            if not rec.shopify_prod_tmpl_id:
                shopify_config_rec = rec.shopify_config_id
                if shopify_config_rec != shopify_initial_id:
                    shopify_initial_id = shopify_config_rec
                    log_line_vals.update({
                        'shopify_config_id': shopify_initial_id.id,
                    })
                    parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

                seconds = self.env.context.get('queue_job_second') or 5
                eta = datetime.now() + timedelta(seconds=seconds)
                name = rec.product_tmpl_id.display_name or ''
                job_descr = _("Export Product Template to Shopify:   %s") % (
                        name and name.strip())
                log_line_id = shopify_log_line_obj.create({
                    'name': job_descr,
                    'shopify_config_id': shopify_config_rec.id,
                    'id_shopify': rec.shopify_prod_tmpl_id or '',
                    'operation_type': 'export_product',
                    'parent_id': parent_log_line_id.id
                })
                shopify_config_rec.with_company(shopify_config_rec.default_company_id).with_delay(
                    description=job_descr, max_retries=5,
                    eta=eta).export_product(rec, log_line_id=log_line_id)
            if parent_log_line_id:
                parent_log_line_id.update({
                    'state': 'success',
                    'message': 'Operation Successful'
                })

    def shopify_import_product(self, shopify_config):
        """This method is used to create queue and queue line for products"""
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Products",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_product',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            shopify_config.check_connection()
            shopify_product_list = self_cr.fetch_all_shopify_products(shopify_config)
            if shopify_product_list:
                seconds = 5
                for product in shopify_product_list:
                    product_dict = product.to_dict()
                    name = product_dict.get('title', '') or ''
                    eta = datetime.now() + timedelta(minutes=1, seconds=seconds)
                    job_descr = _("Create/Update Product:   %s") % (
                            name and name.strip())
                    log_line_vals.update({
                        'name': job_descr,
                        'id_shopify': product_dict.get('id') or '',
                        'parent_id': parent_log_line_id.id
                    })
                    log_line_id = shopify_log_line_obj.create(log_line_vals)
                    self_cr.env['shopify.product.template'].with_company(shopify_config.default_company_id).with_delay(
                        description=job_descr, max_retries=5,
                        eta=eta).create_update_shopify_product(
                        product_dict, shopify_config, log_line_id)
                    seconds += 2
            key_name = 'shopify_config_%s' % (str(shopify_config.id))
            parameter_id = self.env['ir.config_parameter'].search([('key', '=', key_name)])
            shopify_config.get_update_value_from_config(
                operation='write', field='last_product_import_date', shopify_config_id=shopify_config,
                field_value=str(datetime.now().strftime('%Y/%m/%d %H:%M:%S')), parameter_id=parameter_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            cr.commit()
            return True
        except Exception as e:
            cr.rollback()
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def odoo_product_search_sync(self, shopify_config_id, sku, barcode):
        sync_product = shopify_config_id.sync_product
        odoo_product = False
        domain_product = []
        if sync_product == 'sku' and sku:
            domain_product = [('default_code', '=', sku)]
        elif sync_product == 'barcode' and barcode:
            domain_product = [('barcode', '=', barcode)]
        elif sync_product == 'sku_barcode':
            if sku and barcode:
                domain_product = [
                    '|', ('default_code', '=', sku), ('barcode', '=', barcode)]
            elif sku and not barcode:
                domain_product = [('default_code', '=', sku)]
            elif not sku and barcode:
                domain_product = [('barcode', '=', barcode)]
        if domain_product:
            domain_product += ['|', ('active', '=', True), ('active', '=', False)]
            odoo_product = self.env['product.product'].sudo().search(
                domain_product, limit=1)
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
            if sku and barcode:
                domain_product = [
                    '|', ('default_code', '=', sku), ('barcode', '=', barcode)]
            elif sku and not barcode:
                domain_product = [('default_code', '=', sku)]
            elif not sku and barcode:
                domain_product = [('barcode', '=', barcode)]
        if domain_product:
            odoo_product = self.env['shopify.product.product'].sudo().search(
                domain_product, limit=1)
        return odoo_product

    def create_variant_product(self, result, price, archived_product_categ_id, shopify_config_id,
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
                attribute = product_attribute_obj.sudo().create(
                    {'name': attrib_name})
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
            detailed_type = 'product' if result.get('variants')[0].get(
                'requires_shipping') else 'service'
            if not archived_product_categ_id and shopify_config_id.product_categ_id:
                product_category = shopify_config_id.product_categ_id
            else:
                product_category = archived_product_categ_id
            product_template = product_template_obj.create(
                {'name': template_title,
                 'type': 'product',
                 'attribute_line_ids': attrib_line_vals,
                 'description_sale': result.get('description', ''),
                 'categ_id': product_category and product_category.id or False,
                 'sale_ok': True,
                 'purchase_ok': True,
                 'weight': result.get('weight', ''),
                 'detailed_type': detailed_type,
                 'type': detailed_type
                 })
            if result.get('variants'):
                is_taxable = any(variant.get('taxable', False) for variant in result.get('variants'))
                if not is_taxable:
                    product_template.update({'taxes_id': False})
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
            weight = variation.get('weight')
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
                product_id = odoo_product_obj.search([
                    ('product_tmpl_id', '=', product_template.id), '|',
                    ('active', '=', False), ('active', '=', True)])
                pt_atribt_ids = product_id.product_template_attribute_value_ids
                attribute_ids = pt_atribt_ids.filtered(
                    lambda a: a.product_attribute_value_id.id in
                              attribute_value_ids)
                odoo_product = product_id.filtered(
                    lambda a: a.product_template_attribute_value_ids ==
                              attribute_ids)
                if odoo_product:
                    odoo_product and odoo_product.write({'default_code': sku})
                # TODO: remove comment after update shopify product duplicate barcode
                vals_to_update = {}
                if barcode:
                    vals_to_update.update({'barcode': barcode})
                if price:
                    vals_to_update.update({'list_price': price,
                                           'lst_price': price})
                if result.get('title'):
                    vals_to_update.update({'name': result.get('title')})
                if result.get('body_html'):
                    vals_to_update.update({'shopify_description': result.get('body_html')})
                if weight and weight > 0:
                    vals_to_update.update({'weight': weight})
                # for shopify product variant
                if odoo_product:
                    for product in odoo_product:
                        if not product.shopify_product_product_ids:
                            vals_to_update.update({'shopify_product_product_ids': [
                                (0, 0, {
                                    'product_template_id': product.product_tmpl_id.id,
                                    'shopify_config_id': shopify_config_id.id,
                                    'shopify_product_id': variant_id,
                                    'lst_price': price,
                                    'shopify_inventory_item_id': inventory_item_id,
                                    'shopify_product_template_id': shopify_prd_tmpl_id.id,
                                    'company_id':
                                        shopify_config_id.default_company_id and
                                        shopify_config_id.default_company_id.id or False,
                                    'shopify_inventory_management': True if variation.get(
                                        'inventory_management') == 'shopify' else False,
                                    'shopify_inventory_policy': True if variation.get(
                                        'inventory_policy') == 'continue' and variation.get(
                                        'inventory_management') == 'shopify' else False,
                                    'include_tax': True if variation.get(
                                        'taxable') else False
                                })]})
                        elif not product.shopify_product_product_ids.filtered(
                                lambda p: p.shopify_config_id.id ==
                                          shopify_config_id.id):
                            product.shopify_product_product_ids.create({
                                'product_template_id': product.product_tmpl_id.id,
                                'shopify_config_id': shopify_config_id.id,
                                'shopify_product_id': variant_id,
                                'product_variant_id': product.id,
                                'lst_price': price,
                                'shopify_inventory_item_id': inventory_item_id,
                                'shopify_product_template_id': shopify_prd_tmpl_id.id,
                                'company_id':
                                    shopify_config_id.default_company_id and
                                    shopify_config_id.default_company_id.id or False,
                                'shopify_inventory_management': True if variation.get(
                                    'inventory_management') == 'shopify' else False,
                                'shopify_inventory_policy': True if variation.get(
                                    'inventory_policy') == 'continue' and variation.get(
                                    'inventory_management') == 'shopify' else False,
                                'include_tax': True if variation.get(
                                    'taxable') else False
                            })
                        else:
                            shopify_prod_id = product.shopify_product_product_ids.filtered(
                                lambda p: p.shopify_config_id.id ==
                                          shopify_config_id.id and
                                          p.shopify_product_id and
                                          p.shopify_product_id ==
                                          str(variant_id))
                            shopify_prod_id.write({
                                'lst_price': price,
                                'shopify_inventory_management': True if variation.get(
                                    'inventory_management') == 'shopify' else False,
                                'shopify_inventory_policy': True if variation.get(
                                    'inventory_policy') == 'continue' and variation.get(
                                    'inventory_management') == 'shopify' else False,
                                'include_tax': True if variation.get(
                                    'taxable') else False
                            })
                    if not odoo_product.active:
                        vals_to_update.update({'active': True})
                    # if product exists and product has barcode and
                    # weight do not override
                    if vals_to_update.get('barcode') and odoo_product.barcode:
                        del vals_to_update['barcode']

                    if vals_to_update.get('weight') and odoo_product.weight > 0:
                        del vals_to_update['weight']
                    odoo_product.write(vals_to_update)
                    if not odoo_product.product_tmpl_id.active:
                        odoo_product.product_tmpl_id.write({'active': True})

    def _remove_old_magento_product(self, product_dict):
        sku_list = []
        for variant in product_dict.get('variants'):
            sku_list.append(variant.get('sku', ''))
        prod_ids = self.env['product.product'].search([
            ('default_code', 'in', sku_list), '|', ('active', '=', False),
            ('active', '=', True)])
        archived_product_categ_id = False
        if prod_ids and (len(set(prod_ids.mapped('product_tmpl_id.id'))) != 1 or len(
                prod_ids.mapped('product_tmpl_id.product_variant_ids.id')) == 1):
            for prod in prod_ids:
                if prod.product_tmpl_id.categ_id:
                    archived_product_categ_id = prod.product_tmpl_id.categ_id
                    break
            for prod in prod_ids.filtered(lambda p: not p.shopify_product_product_ids):
                vals = {
                    'active': False,
                }
                if prod.default_code:
                    vals.update({
                        'default_code': str(prod.default_code) + '-MAGENTO-OLD',
                    })
                if prod.barcode:
                    vals.update({
                        'barcode': prod.barcode + '-MAGENTO-OLD' if prod.barcode else '',

                    })
                prod.write(vals)
                prod.product_tmpl_id.write(vals)
        return archived_product_categ_id

    def update_product_attribute_lines(self, product_dict,
                                       product_tmpl_id, shopify_config_id):
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        is_variant_products = len(product_dict.get('variants')) > 1
        if not is_variant_products:
            return

        ctx = dict(self.env.context)
        ctx.update({'from_shopify_import': True, 'shopify_config_id': shopify_config_id})
        attribute_ids = []
        for each_option_line in product_dict.get('options'):
            attrib_name = each_option_line.get('name')
            attrib_values = each_option_line.get('values')
            attr_val_ids = []

            attribute_id = product_attribute_obj.search(
                [('name', '=', attrib_name)], limit=1)
            if not attribute_id:
                attribute_id = product_attribute_obj.create(
                    {'name': attrib_name})
            if attribute_id:
                attribute_ids.append(attribute_id.id)

            for att_value in attrib_values:
                attrib_value_id = product_attribute_value_obj.search(
                    [('attribute_id', '=', attribute_id.id),
                     ('name', '=', att_value)], limit=1)
                if not attrib_value_id:
                    attrib_value_id = product_attribute_value_obj.with_context(
                        active_id=False).create(
                        {'attribute_id': attribute_id.id, 'name': att_value})

                attr_val_ids.append(attrib_value_id.id)

            attribute_line = product_tmpl_id.attribute_line_ids.filtered(
                lambda line: line.attribute_id == attribute_id)

            if attribute_line and attr_val_ids:
                for line in attr_val_ids:
                    if line not in attribute_line.value_ids.ids:
                        product_tmpl_id.write({
                            'attribute_line_ids': [(1, attribute_line.id, {
                                'value_ids': [[4, line]]
                            })]
                        })
                for exist_line in attribute_line.value_ids:
                    if exist_line.id not in attr_val_ids:
                        product_tmpl_id.with_context(ctx).write({
                            'attribute_line_ids': [(1, attribute_line.id, {
                                'value_ids': [[3, exist_line.id]]
                            })]
                        })
            if not attribute_line and attr_val_ids and attribute_id:
                attribute_line_ids_data = [
                    [0, 0, {
                        'attribute_id': attribute_id.id,
                        'value_ids': [[6, False, attr_val_ids]]}]]
                product_tmpl_id.write({'attribute_line_ids': attribute_line_ids_data})

        if attribute_ids:
            attribute_line = product_tmpl_id.attribute_line_ids.filtered(
                lambda line: line and line.attribute_id.id not in attribute_ids)
            attribute_line.with_context(ctx).unlink()

    def create_update_shopify_product(self, product_dict, shopify_config_id, log_line_id):
        """Fetch a product from shopify"""
        shopify_config_id.check_connection()
        shopify_product_obj = self.env['shopify.product.product']
        product_template_obj = self.env['product.template']
        product_category_obj = self.env['product.category']
        partner_obj = self.env['res.partner']
        try:
            is_service_product = False
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
            product_id_list = []
            for variant in product_dict.get('variants'):
                odoo_product = False
                supplier = False
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
                # shopify_variant = shopify_product_obj.search(
                #     [('product_variant_id', '=', variant_id),
                #      ('shopify_config_id', '=', shopify_config_id.id)], limit=1)
                sync_product = shopify_config_id.sync_product
                error_msg = self.check_product_sync(
                    sku, barcode, template_title, variant_id, sync_product)
                if error_msg:
                    raise ValidationError(_(error_msg))

                # assign All category
                product_category = False

                if not shopify_template:
                    if product_type.strip():
                        product_category = product_category_obj.search(
                            [('name', '=', product_type.strip())], limit=1)
                        if not product_category:
                            # product_category = shopify_config_id.product_categ_id
                            # else:
                            #     product_category = self.env.ref(
                            #         'product.product_category_all')
                            product_category = product_category_obj.create(
                                {'name': product_type.strip(),
                                 'property_cost_method': 'fifo',
                                 'property_valuation': 'real_time',
                                 })
                    else:
                        if shopify_config_id.product_categ_id:
                            product_category = shopify_config_id.product_categ_id
                        else:
                            product_category = self.env.ref(
                                'product.product_category_all')

                if not product_category:
                    product_category = self.env.ref(
                        'product.product_category_all')
                if vendor:
                    supplier = partner_obj.search([
                        ('name', '=', vendor),
                        ('supplier_rank', '>', 0),
                        ('company_id', '=',
                         shopify_config_id.default_company_id.id)], limit=1)
                    if not supplier:
                        supplier = partner_obj.create({
                            'name': vendor,
                            'supplier_rank': 1,
                            'company_id':
                                shopify_config_id.default_company_id.id})

                # shopify tags
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

                if not odoo_product:
                    if len(product_dict.get('variants')) > 1 and \
                            title != 'Default Title':
                        archived_product_categ_id = self._remove_old_magento_product(product_dict)
                        odoo_product = self.odoo_product_search_sync(
                            shopify_config_id, sku, barcode)
                        product_tmpl_id = odoo_product and odoo_product.product_tmpl_id or False
                        if not product_tmpl_id and shopify_template:
                            product_tmpl_id = shopify_template.product_tmpl_id
                        if product_tmpl_id:
                            shopify_product = self.env[
                                'shopify.product.template'].search_count(
                                [('product_tmpl_id', '=', product_tmpl_id.id),
                                 ('shopify_config_id', '=',
                                  shopify_config_id.id),
                                 ('shopify_prod_tmpl_id', '!=',
                                  str(shopify_tmpl_id))])
                            if shopify_product >= 1:
                                error_message = "You cannot create multiple records for same shopify " \
                                                "configuration for product %s: %s" % (
                                                    odoo_product.name, sku)
                                raise ValidationError(_(error_message))
                            self.update_product_attribute_lines(
                                product_dict, product_tmpl_id, shopify_config_id)
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
                                raise ValidationError(_(error_message))
                            else:
                                # create product template
                                if shopify_config_id.is_create_product:
                                    product_tmpl_id = self.create_variant_product(
                                        product_dict, price, archived_product_categ_id,
                                        shopify_config_id, is_service_product)
                                    if list_of_tags and product_tmpl_id:
                                        product_tmpl_id.write(
                                            {'prod_tags_ids': [
                                                (6, 0, list_of_tags)]})
                                else:
                                    error_message = "Odoo product not created for %s.\n" \
                                                    "if you want auto created it. enable it from shopify configuration" % (
                                                        template_title)
                                    raise ValidationError(_(error_message))

                        tmpl_id = product_tmpl_id
                        if not tmpl_id:
                            error_message = "Odoo product not created for %s.\n" \
                                            "if you want auto created it. enable it from shopify configuration" % (
                                                template_title)
                            raise ValidationError(_(error_message))
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
                                'product_type': product_category.id,
                                'shopify_prod_tmpl_id': shopify_tmpl_id,
                                'body_html': body_html,
                                'shopify_published': True,
                                'company_id':
                                    shopify_config_id.default_company_id.id,
                                'shopify_published_scope': shopify_published_scope,
                                'shopify_handle': handle,
                            }
                            if supplier:
                                shopify_tmpl_vals.update({
                                    'vendor': supplier.id})

                            if not shopify_product_templates:
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
                            raise ValidationError(_(error_message))
                        # for images
                        if product_tmpl_id and shopify_tmpl_id and \
                                shopify_config_id.is_sync_product_image:
                            self.sync_shopify_product_images(product_tmpl_id,
                                                             shopify_tmpl_id)
                        product_id_list = product_tmpl_id.product_variant_ids.ids
                    # for product without variants
                    else:
                        odoo_product = self.odoo_product_search_sync(
                            shopify_config_id, sku, barcode)
                        tmpl_id = odoo_product and odoo_product.product_tmpl_id
                        # for creating Odoo product.template
                        detailed_type = 'product' if product_dict.get('variants')[0].get(
                            'requires_shipping') else 'service'
                        is_taxable = product_dict.get('variants')[0].get('taxable') if product_dict.get('variants') else False
                        temp_vals = {
                            'name': template_title,
                            'sale_ok': True,
                            'purchase_ok': True,
                            'published_on_shopify': True,
                            'shopify_description': body_html,
                            'default_code': sku or '',
                            'type': 'product',
                            'list_price': price,
                            'weight': weight,
                            'detailed_type': detailed_type,
                            'type': detailed_type

                        }
                        if not is_taxable:
                            temp_vals.update({'taxes_id': False})
                        if shopify_config_id.product_categ_id:
                            temp_product_category = shopify_config_id.product_categ_id
                        else:
                            temp_product_category = self.env.ref(
                                'product.product_category_all')
                        if temp_product_category and not tmpl_id:
                            temp_vals.update({
                                'categ_id': temp_product_category and
                                            temp_product_category.id or False})
                        if barcode:
                            temp_vals.update({'barcode': barcode or ''})
                        # set the service type and invoicing policy
                        # if is_service_product:
                        #     temp_vals.update({
                        #         'type': 'service',
                        #         'invoice_policy': 'order'
                        #     })

                        if list_of_tags:
                            temp_vals.update(
                                {'prod_tags_ids': [(6, 0, list_of_tags)]})
                        # create product template
                        if shopify_config_id.is_create_product and not tmpl_id:
                            tmpl_id = product_template_obj.create(temp_vals)
                        elif tmpl_id:
                            # if product exists and product has barcode and
                            # weight do not override
                            if temp_vals.get('barcode') and tmpl_id.barcode:
                                del temp_vals['barcode']
                            if temp_vals.get('weight') and tmpl_id.weight > 0:
                                del temp_vals['weight']
                            tmpl_id.update(temp_vals)
                        else:
                            error_message = "Odoo product not created for %s.\n" \
                                            "if you want auto created it. enable it from shopify configuration" % (
                                                template_title)
                            raise ValidationError(_(error_message))

                        # for shopify product template
                        shopify_prd_tmpl_id = self.search(
                            [('shopify_prod_tmpl_id', '=',
                              str(shopify_tmpl_id)),
                             ('shopify_config_id', '=', shopify_config_id.id)])
                        # TODO: collection (New API doesnot support it. So need to do R&D based on collection API)

                        shopify_tmpl_vals = {
                            'product_tmpl_id': tmpl_id.id,
                            'shopify_config_id': shopify_config_id.id,
                            'product_type': product_category.id,
                            'shopify_prod_tmpl_id': shopify_tmpl_id,
                            'body_html': body_html,
                            'shopify_published': True,
                            'company_id': shopify_config_id.default_company_id.id,
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
                            raise ValidationError(_(error_message))
                        if shopify_prd_tmpl_id:
                            shopify_prd_tmpl_id.update(shopify_tmpl_vals)
                        else:
                            shopify_prd_tmpl_id = self.create(
                                shopify_tmpl_vals)
                        # for shopify product variant
                        s_prd_id = shopify_product_obj.search([
                            ('shopify_product_id', '=', variant.get('id')),
                            ('shopify_config_id', '=', shopify_config_id.id)])
                        odoo_product = self.odoo_product_search_sync(
                            shopify_config_id, sku, barcode)
                        odoo_product.write({
                            'lst_price': price
                        })
                        s_prd_vals = {
                            'product_variant_id': odoo_product.id,
                            'product_template_id': tmpl_id.id,
                            'shopify_config_id': shopify_config_id.id,
                            'shopify_product_id': variant.get('id'),
                            'shopify_inventory_management': True if variant.get(
                                'inventory_management') == 'shopify' else False,
                            'shopify_inventory_policy': True if variant.get(
                                'inventory_policy') == 'continue' and variant.get(
                                'inventory_management') == 'shopify' else False,
                            'lst_price': price,
                            'shopify_inventory_item_id': inventory_item_id,
                            'shopify_product_template_id':
                                shopify_prd_tmpl_id.id,
                            'company_id':
                                shopify_config_id.default_company_id and
                                shopify_config_id.default_company_id.id or False,
                            'include_tax': True if variant.get('taxable') else False
                        }
                        # if product_category:
                        #     odoo_product.write({'categ_id': product_category and
                        #                                     product_category.id or False, })
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
                            raise ValidationError(_(error_message))
                        product_id_list.append(odoo_product.id)
            array_of_strings = [str(num) for num in product_id_list]
            log_line_id.sudo().write({
                'state': 'success',
                'related_model_name': 'product.product',
                'related_model_id': ",".join(array_of_strings),
                'message': 'Operation Successful'
            })
        except Exception as e:
            error_message = "Facing a problem while importing Product!: %s" % e
            log_line_id.sudo().write({
                'state': 'error',
                'message': error_message
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def sync_shopify_product_images(self, product_tmpl_id, shopify_tmpl_id):
        """
            Sync Product Image from shopify and create in odoo.

            find all image and create in odoo product.template multi image tab.
            if image dictionary have variant_ids columns then write
            updated image on product.prodduct table thumbnail image.

            Write single image on Product.Template Thumbnail Image.
        """

        shopify_product_obj = self.env['shopify.product.product']
        shopify_product_img_obj = self.env['product.multi.images']

        shop_product = shopify.Product().find(shopify_tmpl_id)
        shopify_product_dict = shop_product.to_dict()
        product_multi_images = shopify_product_dict.get('images')
        product_tmpl_image = shopify_product_dict.get('image')

        for each_image in product_multi_images:
            if each_image.get('src'):
                shopify_image_id = each_image.get('id')
                image = base64.b64encode(requests.get(
                    each_image.get('src').strip()).content).replace(b'\n', b'')
                if image:
                    if each_image.get('variant_ids'):
                        shopify_variant_ids = shopify_product_obj.search(
                            [('shopify_product_id', 'in',
                              each_image['variant_ids'])])
                        if shopify_variant_ids:
                            shopify_variant_ids.mapped(
                                'product_variant_id').write(
                                {'image_1920': image})
                    else:
                        shopify_gallery_image = shopify_product_img_obj.search_count(
                            [('product_template_id', '=', product_tmpl_id.id),
                             ('shopify_image_id', '=', shopify_image_id)])
                        if not shopify_gallery_image:
                            product_multi_images_vals = {'image': image,
                                                         'description': product_tmpl_id.name,
                                                         'shopify_image_id': shopify_image_id,
                                                         'title': product_tmpl_id.name,
                                                         'product_template_id': product_tmpl_id.id
                                                         }
                            shopify_product_img_obj.create(
                                product_multi_images_vals)

        if product_tmpl_image and product_tmpl_image.get('src'):
            shopify_template_id = self.env['shopify.product.template'].search(
                [('shopify_prod_tmpl_id', '=', str(shopify_tmpl_id))])
            image = base64.b64encode(requests.get(
                product_tmpl_image.get('src').strip()).content).replace(b'\n',
                                                                        b'')
            if shopify_template_id and image:
                shopify_template_id.mapped('product_tmpl_id').write(
                    {'image_1920': image})

    def fetch_all_shopify_inventory_level(self, shopify_config, shopify_location_ids):
        try:
            shopify_inventory_level_list, page_info = [], False
            while 1:
                last_stock_import_date, parameter_id = shopify_config.get_update_value_from_config(
                    operation='read', field='last_stock_import_date', shopify_config_id=shopify_config,
                    field_value='')

                if last_stock_import_date:
                    if page_info:
                        page_wise_inventory_list = shopify.InventoryLevel().find(page_info=page_info)
                    else:
                        page_wise_inventory_list = shopify.InventoryLevel().find(
                            updated_at_min=last_stock_import_date or fields.Datetime.now(),
                            location_ids=','.join(shopify_location_ids))
                else:
                    if page_info:
                        page_wise_inventory_list = shopify.InventoryLevel().find(page_info=page_info)
                    else:
                        page_wise_inventory_list = shopify.InventoryLevel().find(
                            location_ids=','.join(shopify_location_ids))
                page_url = page_wise_inventory_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and parsed.get(
                    'page_info', False)[0] or False
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
                location_wise_inventory_dict[shopify_location_id].append(
                    inventory_level)
            else:
                location_wise_inventory_dict.update(
                    {shopify_location_id: [inventory_level]})
        return location_wise_inventory_dict

    def prepare_inv_adjustment_lines(self, inventory_level_list, shopify_config, shopify_location_id):
        product_variant_ids, inventory_line_list = self.env['product.product'], [
        ]
        for inventory_level in inventory_level_list:
            shopify_inventory_item_id = inventory_level.get(
                'inventory_item_id')
            qty = inventory_level.get('available', 0) or 0
            shopify_product = self.env['shopify.product.product'].search(
                [('product_variant_id.type', '!=', 'service'),
                 ('product_variant_id.tracking', '=', 'none'),
                 ('update_shopify_inv', '=', True),
                 ('shopify_inventory_item_id', '=', shopify_inventory_item_id),
                 ('shopify_config_id', '=', shopify_config.id)], limit=1)
            if shopify_product:
                odoo_product_id = shopify_product.product_variant_id
                # if not any([line[2].get('product_id') == odoo_product_id.id for line in inventory_line_list]):
                if not any([line.get('product_id') == odoo_product_id.id for line in inventory_line_list]):
                    product_variant_ids += odoo_product_id
                    location_mapping_id = self.env['shopify.location.mapping'].search([
                        ('shopify_location_id', '=', shopify_location_id),
                        ('shopify_config_id', '=', shopify_config.id),
                        ('odoo_location_id', '!=', False)], limit=1)
                    # location_id = self.env['stock.location'].search(
                    #     [('shopify_config_id', '=', shopify_config.id),
                    #      ('usage', '=', 'internal'),
                    #      ('shopify_location_id', '=', shopify_location_id)],
                    #     limit=1)
                    # inventory_line_list.append((0, 0, {"product_id": odoo_product_id.id,
                    #                                    "location_id": location_id.id,
                    #                                    "product_qty": qty if qty > 0 else 0}))
                    if location_mapping_id:
                        inventory_line_list.append({"product_id": odoo_product_id.id,
                                                    "product_name": odoo_product_id.display_name,
                                                    "product_shopify_id": shopify_product.shopify_product_id,
                                                    "location_id": location_mapping_id.odoo_location_id.id,
                                                    "inventory_quantity": qty if qty > 0 else 0})
                    else:
                        raise ValidationError(_('Please set odoo location for shopify location-> %s!'),
                                              shopify_location_id)
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
    def create_process_inventory_adjustment(self, shopify_config, inventory_line_list, log_line_id):
        Quant = self.env['stock.quant'].sudo().with_context(inventory_mode=True)
        # Commented to avoid recurring live sync from odoo to shopify when set to False.
        # When this boolean is False, User will have to manually click on 'Apply' button in stock quants and
        # this will update stock on shopify through live sync feature
        # validate_inv = shopify_config.is_validate_inv_adj
        try:
            quant_id = Quant.sudo().create(inventory_line_list)
            # if validate_inv:
            #     quant_id.with_context(shopify_adjustment=True).action_apply_inventory()
            quant_id.with_context(
                shopify_adjustment=True).action_apply_inventory()
            log_line_id.update({
                'state': 'success',
                'related_model_name': 'stock.quant',
                'related_model_id': quant_id.id,
            })
        except Exception as e:
            log_line_id.update({
                'state': 'error',
                'message': 'Failed to import Stock : {}'.format(e)
            })

    # def cancel_existing_inventory_adjustments(self):
    #     inventory_adjuts_obj = self.env['stock.inventory']
    #     for inv in inventory_adjuts_obj.search([('shopify_adjustment', '=', True),
    #                                             ('state', '!=', 'done')]):
    #         if not inv.state == 'cancel':
    #             inv.action_cancel_draft()
    #             inv.write({'state': 'cancel'})

    def shopify_import_stock(self, shopify_config):

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Stock",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_stock',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            # error_log_env = self_cr.env['shopify.error.log']
            # shopify_log_id = error_log_env.create_update_log(
            #     shopify_config_id=shopify_config,
            #     operation_type='import_stock')
            shopify_product_template_ids = self_cr.search(
                [('shopify_config_id', '=', shopify_config.id)])
            # self.cancel_existing_inventory_adjustments()
            if shopify_product_template_ids:
                shopify_config.check_connection()
                # added search from location mapping table instead of the direct location search.
                location_mapping_ids = self_cr.env['shopify.location.mapping'].search([
                    ('shopify_location_id', '!=', False),
                    ('shopify_config_id', '=', shopify_config.id),
                    ('odoo_location_id', '!=', False)])
                # location_ids = self.env['stock.location'].search(
                #     [('shopify_config_id', '=', shopify_config.id),
                #      ('shopify_location_id', '!=', False)])

                name_mapping_dict = {
                    location.shopify_location_id: location.odoo_location_id.display_name
                    for location in location_mapping_ids
                }

                shopify_location_ids = location_mapping_ids.mapped('shopify_location_id')
                shopify_inventory_levels = self_cr.fetch_all_shopify_inventory_level(
                    shopify_config, shopify_location_ids)
                location_wise_inventory_dict = self_cr.prepare_location_wise_inventory_level(
                    shopify_inventory_levels)
                for shopify_location_id, inventory_level_list in location_wise_inventory_dict.items():
                    # try:
                    inventory_line_list, product_variant_ids = self_cr.prepare_inv_adjustment_lines(
                        inventory_level_list, shopify_config, shopify_location_id)
                    for vals in inventory_line_list:
                        name = "%s - %s" % (name_mapping_dict.get(str(shopify_location_id)),
                                            vals.get('product_name', ''))
                        job_descr = _("Create/Update Stock in ODOO: %s") % (name and name.strip())

                        log_line_vals.update({
                            'name': job_descr,
                            'id_shopify': f"Location: {shopify_location_id or ''} Product: {vals.get('product_shopify_id', '')}",
                            'parent_id': parent_log_line_id.id
                        })
                        log_line_id = shopify_log_line_obj.create(log_line_vals)

                        vals.pop('product_name')
                        vals.pop('product_shopify_id')
                        self_cr.with_company(shopify_config.default_company_id).with_delay(description=job_descr, max_retries=5).create_process_inventory_adjustment(
                            shopify_config, vals, log_line_id)
                        # if inventory_adjustment_id:
                        #     log_message = "Imported Stock Successfully. Review Inventory Adjustment: %s" % (
                        #         inventory_adjustment_id.name)
                        #     error_log_env.create_update_log(
                        #         shop_error_log_id=shopify_log_id,
                        #         shopify_log_line_dict={
                        #             'error': [{'error_message': log_message}]})
                    # except Exception as e:
                    #     log_message = "Facing a problem while importing Stock: %s" % (
                    #         e)
                    #     error_log_env.create_update_log(
                    #         shop_error_log_id=shopify_log_id,
                    #         shopify_log_line_dict={
                    #             'error': [{'error_message': log_message}]})
                    #     return False
                # if not shopify_log_id.shop_error_log_line_ids:
                #     shopify_log_id.unlink()
            key_name = 'shopify_config_%s' % (str(shopify_config.id))
            parameter_id = self.env['ir.config_parameter'].search([('key', '=', key_name)])
            shopify_config.get_update_value_from_config(
                operation='write', field='last_stock_import_date', shopify_config_id=shopify_config,
                field_value=str(datetime.now().strftime('%Y/%m/%d %H:%M:%S')), parameter_id=parameter_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            cr.commit()
            return True
        except Exception as e:
            cr.rollback()
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))
