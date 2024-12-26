##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from .. import shopify
import logging

from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ShopifyProductProduct(models.Model):
    _name = 'shopify.product.product'
    _description = 'Shopify Product Variant'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'product_variant_id'

    @api.depends("product_variant_id")
    def _set_prod_template(self):
        """ Set product template according product variant """
        for rec in self:
            tmpl_id = rec.product_variant_id and \
                rec.product_variant_id.product_tmpl_id.id or False
            rec.product_template_id = tmpl_id

    shopify_product_template_id = fields.Many2one(
        "shopify.product.template",
        "Shopify Product Template",
        help="Select Shopify Product Template",
        tracking=True,
        readonly=True, copy=False)
    shopify_product_id = fields.Char(
        "Shopify Product Variant",
        help="Enter Shopify Product Variant",
        tracking=True,
        readonly=True, copy=False)
    shopify_config_id = fields.Many2one(
        "shopify.config",
        "Shopify Config",
        help="Enter Shopify Config.",
        tracking=True,
        required=True, copy=False)
    shopify_inventory_item_id = fields.Char(
        "Shopify Inventory Item",
        help="Enter Shopify Inventory Item",
        tracking=True,
        readonly=True, copy=False)
    shopify_published_variant = fields.Boolean(
        "Shopify Published Variant",
        default=True,
        help="Check if Shopify Published Variant or not?",
        tracking=True,
        readonly=True, copy=False)
    product_template_id = fields.Many2one(
        "product.template",
        "Product Template",
        help="Enter Product Template",
        compute="_set_prod_template",
        tracking=True,
        store=True, copy=False)
    product_variant_id = fields.Many2one(
        "product.product",
        "Product Variant",
        help="Enter Product Variant",
        tracking=True,
        required=True, copy=False)
    default_code = fields.Char(
        "Default Code",
        help="Enter Default Code",
        related="product_variant_id.default_code",
        readonly=True,
        tracking=True, copy=False)
    lst_price = fields.Float(
        string='Sale Price',
        help="Sale price for Shopify",
        required=True, copy=False)

    shopify_uom = fields.Many2one("uom.uom",
                                  string="UOM",
                                  help="UOM of product",
                                  related="product_variant_id.uom_id",
                                  readonly=True)
    last_updated_date = fields.Datetime(string='Last Updated Date',
                                        readonly=True, copy=False)
    update_shopify_inv = fields.Boolean("Update Shopify Inventory?",
                                        copy=False, default=True)
    is_new_variant = fields.Boolean("Is New Variant?", copy=False)
    barcode = fields.Char(
        "Barcode",
        help="Barcode",
        related="product_variant_id.barcode",
        readonly=True,
        tracking=True, copy=False)
    include_tax = fields.Boolean(
        "Is Include Tax?",
        default=False,
        help="Check if variant has tax or not?",
        tracking=True,
        copy=False)
    company_id = fields.Many2one('res.company', string="Company")

    shopify_inventory_management = fields.Boolean(string="Track Quantity", default=True)
    shopify_inventory_policy = fields.Boolean(string="Continue Selling When Out of Stock", default=True)
    variant_ready_for_update = fields.Boolean(string="Ready for Update", default=False)

    @api.onchange("shopify_inventory_management")
    def _onchange_shopify_track_quantity(self):
        if not self.shopify_inventory_management:
            self.shopify_inventory_policy = False

    # @api.model
    # def create(self, vals):
    #     """
    #     Prevent the user to create a shopify product product record with the
    #     same shopify config.
    #     """
    #     res = super(ShopifyProductProduct, self).create(vals)
    #     product_variant_id = vals.get('product_variant_id')
    #     shopify_config_id = vals.get('shopify_config_id')
    #     shopify_product_variants_count = self.search_count(
    #         [('product_variant_id', '=', product_variant_id),
    #          ('shopify_config_id', '=', shopify_config_id),
    #          ('id', '!=', res.id)])
    #     if shopify_product_variants_count >= 1:
    #         raise ValidationError(
    #             _("You cannot create multiple records for same shopify "
    #               "configuration. %s" % product_variant_id))
    #     return res
    #
    # def write(self, vals):
    #     """
    #     Prevent the user to update a shopify product product record with the
    #     same shopify config.
    #     """
    #     res = super(ShopifyProductProduct, self).write(vals)
    #     for rec in self:
    #         product_variant_id = rec.product_variant_id.id
    #         shopify_config_id = vals.get('shopify_config_id')
    #         shopify_product_variants_count = self.search_count(
    #             [('product_variant_id', '=', product_variant_id),
    #              ('shopify_config_id', '=', shopify_config_id),
    #              ('id', '!=', rec.id)])
    #         if shopify_product_variants_count >= 1:
    #             raise ValidationError(
    #                 _("You cannot create multiple records for same shopify "
    #                   "configuration %s" % product_variant_id))
    #     return res

    def export_shopify_variant(self, parent_log_line_id):
        """
        This method gets called by export variant button and
        calls the export_prod_variant method on shopify config master
        """
        shopify_log_line_obj = self.env['shopify.log.line']
        for rec in self:
            shopify_config_rec = rec.shopify_config_id
            seconds = self.env.context.get('queue_job_second') or 5
            eta = datetime.now() + timedelta(seconds=seconds)
            name = rec.product_variant_id.display_name or ''
            job_descr = _("Export Product Variant to Shopify:   %s") % (
                    name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config_rec.id,
                'id_shopify': rec.shopify_product_id or '',
                'operation_type': 'export_product',
                'parent_id': parent_log_line_id.id
            })
            shopify_config_rec.with_company(shopify_config_rec.default_company_id).with_delay(
                    description=job_descr, max_retries=5,
                    eta=eta).export_prod_variant(rec, log_line_id=log_line_id)

    def update_shopify_variant_btn(self):
        '''button method from product form view to update product
        from shopify to odoo'''
        seconds = 5
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {}
        for product in self:
            log_line_vals.update({
                'shopify_config_id': product.shopify_config_id.id,
                'name': "Update Product Variant to Shopify",
                'operation_type': 'update_product',
            })
            parent_log_line_id = shopify_log_line_obj.create(
                log_line_vals)
            eta = datetime.now() + timedelta(seconds=seconds)
            job_descr = ("Update Product:   %s") % (
                    product.product_variant_id.name or '')
            log_line_vals.update({
                'name': job_descr,
                'id_shopify': product.shopify_product_id,
                'parent_id': parent_log_line_id.id
            })
            log_line_id = shopify_log_line_obj.create(log_line_vals)
            product.with_company(product.shopify_config_id.default_company_id).with_delay(
                description="Update Variant to Shopify", max_retries=5,
                eta=eta).update_shopify_variant(log_line_id)

    def update_shopify_variant(self, log_line_id):
        """
        Process shopify product variant update from odoo to shopify

        1. Check the connection of odoo with shopify.
        2. Get the respective field values like product_variant_default_code, product_variant_price,
           shopify_product_variant_id, shopify_product_template_id.
        3. If the product and variant are existing on shopify, then only it will update the fields,
            else it will throw validation error.
        4. Set all the fields values on shopify product variant and save the shopify product variant object.
        """
        self.shopify_config_id.check_connection()
        _product_variant_list = []
        product_variant_default_code = ''
        product_variant_barcode = ''
        for rec in self:
            try:
                record_id = rec.id
                product_tmpl_rec = rec.product_template_id
                product_variant_rec = rec.product_variant_id
                if record_id in _product_variant_list:
                    return True
                _product_variant_list.append(record_id)
                if product_tmpl_rec.sale_ok:
                    if self.shopify_config_id.sync_product == 'sku':
                        # if product_variant_rec.default_code:
                        #     product_variant_default_code = str(
                        #         product_variant_rec.default_code)
                        # else:
                        #     raise ValidationError(
                        #         _("Please set Internal Reference for product variant before updating to shopify !"))
                        if not product_variant_rec.default_code:
                            raise ValidationError(
                                _("Please set Internal Reference for product variant before updating to shopify !"))
                    elif self.shopify_config_id.sync_product == 'barcode':
                        # if product_variant_rec.barcode:
                        #     product_variant_barcode = str(
                        #         product_variant_rec.barcode)
                        # else:
                        #     raise ValidationError(
                        #         _("Please set Barcode for product variant before updating to shopify !"))
                        if not product_variant_rec.barcode:
                            raise ValidationError(
                                _("Please set Barcode for product variant before updating to shopify !"))
                    else:
                        # if product_variant_rec.default_code or product_variant_rec.barcode:
                        #     product_variant_default_code = str(
                        #         product_variant_rec.default_code)
                        #     product_variant_barcode = str(
                        #         product_variant_rec.barcode)
                        # else:
                        #     raise ValidationError(
                        #         _("Please set Internal Reference or Barcode for product variant before updating to shopify !"))
                        if (not product_variant_rec.default_code and
                                not product_variant_rec.barcode):
                            raise ValidationError(
                                _("Please set Internal Reference or Barcode for product variant before updating to shopify !"))
                    try:
                        if product_variant_rec.default_code:
                            product_variant_default_code = str(
                                product_variant_rec.default_code)
                        if product_variant_rec.barcode:
                            product_variant_barcode = str(
                                product_variant_rec.barcode)
                        product_variant_price = product_variant_rec.lst_price
                        product_inventory_management = rec.shopify_inventory_management
                        product_inventory_policy = rec.shopify_inventory_policy
                        product_variant_taxable = rec.include_tax
                        shopify_product_variant_id = rec.shopify_product_id
                        product_variant_image = product_variant_rec.image_1920.decode(
                            "utf-8") if product_variant_rec.image_1920 else False
                        shopify_product_template_id = str(
                            rec.shopify_product_template_id.shopify_prod_tmpl_id)
                        shopify_product = shopify.Product(
                            {'id': shopify_product_template_id})
                        is_shopify_variant = shopify.Variant.exists(
                            shopify_product_variant_id)
                        is_shopify_product = shopify.Product.exists(
                            shopify_product_template_id)
                        if is_shopify_variant and is_shopify_product:
                            try:
                                shopify_product_variant = shopify.Variant.find(
                                    shopify_product_variant_id, product_id=shopify_product_template_id)
                            except Exception as e:
                                if record_id in _product_variant_list:
                                    _product_variant_list.remove(record_id)
                                raise ValidationError(
                                    _("Issue comes while finding product on Shopify. Kindly contact to your administrator ! - %e" % (
                                        e)))
                            if not shopify_product_variant:
                                if record_id in _product_variant_list:
                                    _product_variant_list.remove(record_id)
                                raise ValidationError(
                                    _("Product does not exist on Shopify. Kindly contact to your administrator !"))

                            if 'inventory_quantity' in shopify_product_variant.attributes:
                                del shopify_product_variant.attributes["inventory_quantity"]
                            if 'old_inventory_quantity' in shopify_product_variant.attributes:
                                del shopify_product_variant.attributes["old_inventory_quantity"]
                            if 'inventory_quantity_adjustment' in shopify_product_variant.attributes:
                                del shopify_product_variant.attributes["inventory_quantity_adjustment"]

                            count = 1
                            for value in product_variant_rec.product_template_attribute_value_ids:
                                opt_cmd = 'shopify_product_variant.option' + \
                                          str(count) + " = '" + str(value.name) + "'"
                                exec(opt_cmd)
                                count += 1

                            shopify_variant_image = shopify_product_variant.image_id
                            shopify_image_search = shopify.Image.find(
                                product_id=shopify_product_template_id)
                            for image in shopify_image_search:
                                if image.id == shopify_variant_image:
                                    image.destroy()
                            if product_variant_image:
                                image = shopify.Image()
                                image.product_id = shopify_product_template_id
                                image.attachment = product_variant_image
                                image.save()
                                shopify_product_variant.image_id = image.id
                                shopify_product_variant.save()
                            if product_variant_default_code:
                                shopify_product_variant.sku = product_variant_default_code
                            if product_variant_barcode:
                                shopify_product_variant.barcode = product_variant_barcode
                            shopify_product_variant.price = product_variant_price
                            shopify_product_variant.taxable = product_variant_taxable
                            shopify_product_variant.cost = (
                                rec.product_variant_id.standard_price)
                            shopify_product_variant.inventory_management = 'shopify' if product_inventory_management else None
                            shopify_product_variant.inventory_policy = 'continue' if product_inventory_policy else 'deny'
                            # update product weight in shopify
                            shopify_product_variant.weight = product_variant_rec.weight
                            success = shopify_product_variant.save()
                            if success:
                                rec.update({'last_updated_date': datetime.today().strftime(
                                    DEFAULT_SERVER_DATETIME_FORMAT)})

                            if record_id in _product_variant_list:
                                _product_variant_list.remove(record_id)
                        else:
                            if record_id in _product_variant_list:
                                _product_variant_list.remove(record_id)
                            raise ValidationError(
                                _("Product does not exist in shopify!"))
                    except Exception as e:
                        _logger.error(
                            'Error occurs while updating product variant on shopify: %s', e)
                        if record_id in _product_variant_list:
                            _product_variant_list.remove(record_id)
                        pass
                else:
                    if record_id in _product_variant_list:
                        _product_variant_list.remove(record_id)
                    raise ValidationError(
                        _("A Product should be 'Can be Sold' before updation"))
                rec.write({
                    'variant_ready_for_update': False
                })
                log_line_id.update({
                    'state': 'success',
                    'related_model_name': 'shopify.product.product',
                    'related_model_id': rec.id,
                    'message': 'Operation Successful'
                })
            except Exception as e:
                msg = 'Failed to export product variant details : {}'.format(e)
                log_line_id.update({
                    'state': 'error',
                    'message': msg
                })
                raise ValidationError(_(msg))

    def write(self, vals):
        # if self._context.get('params') and self._context.get('params').get('view_type') == 'form':
        if not self._context.get('job_uuid'):
            for rec in self:
                if any(field in vals for field in (
                        'shopify_inventory_management', 'shopify_inventory_policy', 'include_tax',
                        'shopify_product_id')):
                    rec.shopify_product_template_id.write({
                        'ready_to_update': True
                    })
                    vals.update({
                        'variant_ready_for_update': True
                    })
        return super(ShopifyProductProduct, self).write(vals)

    # def remove_variant_from_shopify(self, shopify_config_id, log_line_id):
    #     try:
    #         shopify_config_id.check_connection()
    #         shopify.Product().delete(self.shopify_tmpl_id)
    #         log_line_id.sudo().write({
    #             'state': 'success',
    #             'message': ''
    #         })
    #     except Exception as e:
    #         error_message = ("Facing a problem while delete Product from "
    #                          "shopify !: %s" % e)
    #         log_line_id.sudo().write({
    #             'state': 'error',
    #             'message': error_message
    #         })
    #         self.env.cr.commit()
    #         raise Warning(_(e))
