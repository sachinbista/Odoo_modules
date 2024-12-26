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
import logging

from datetime import datetime
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

    shopify_config_id = fields.Many2one(
        "shopify.config",
        "Shopify Config",
        help="Enter Shopify Config.",
        tracking=True,
        required=True, copy=False)
    shopify_product_template_id = fields.Many2one(
        "shopify.product.template",
        "Shopify Product Template",
        help="Select Shopify Product Template",
        tracking=True,
        readonly=False, copy=False, domain="[('shopify_config_id', '=', shopify_config_id)]")
    shopify_product_id = fields.Char(
        "Shopify Product Variant",
        help="Enter Shopify Product Variant",
        tracking=True,
        readonly=False, copy=False)
    shopify_inventory_item_id = fields.Char(
        "Shopify Inventory Item",
        help="Enter Shopify Inventory Item",
        tracking=True,
         copy=False)
    shopify_published_variant = fields.Boolean(
        "Shopify Published Variant",
        default=True,
        help="Check if Shopify Published Variant or not?",
        tracking=True,
        readonly=False, copy=False)
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
        readonly="0",
        tracking=True, copy=False)
    lst_price = fields.Float(
        string='Sale Price',
        help="Sale price for Shopify",
        required=True, copy=False)

    shopify_uom = fields.Many2one("uom.uom",
                                  string="UOM",
                                  help="UOM of product",
                                  related="product_variant_id.uom_id",
                                  readonly=False)
    last_updated_date = fields.Datetime(string='Last Updated Date',
                                        readonly=False, copy=False)
    update_shopify_inv = fields.Boolean("Update Shopify Inventory?",
                                        copy=False, default=True)

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

    def export_shopify_variant(self):
        """
        This method gets called by export variant button and
        calls the export_prod_variant method on shopify config master
        """
        for rec in self:
            shopify_config_rec = rec.shopify_config_id
            shopify_config_rec.export_prod_variant(rec)

    def update_shopify_variant(self):
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
        for rec in self:
            record_id = rec.id
            product_tmpl_rec = rec.product_template_id
            product_variant_rec = rec.product_variant_id
            if record_id in _product_variant_list:
                return True
            _product_variant_list.append(record_id)

            if product_tmpl_rec.sale_ok and product_tmpl_rec.purchase_ok:
                if product_variant_rec.default_code:
                    product_variant_default_code = str(
                        product_variant_rec.default_code)
                else:
                    raise ValidationError(
                        _("Please set Internal Reference for product variant before updating to shopify !"))
                try:
                    product_variant_price = rec.lst_price
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
                                _("Issue comes while finding product on Shopify. Kindly contact to your administrator ! - %e" % (e)))
                        if not shopify_product_variant:
                            if record_id in _product_variant_list:
                                _product_variant_list.remove(record_id)
                            raise ValidationError(
                                _("Product doesnot exist on Shopify. Kindly contact to your administrator !"))

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
                        shopify_product_variant.sku = product_variant_default_code
                        shopify_product_variant.price = product_variant_price
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
                    _logger.error('Error occurs while updating product variant on shopify: %s', e)
                    if record_id in _product_variant_list:
                        _product_variant_list.remove(record_id)
                    pass
            else:
                if record_id in _product_variant_list:
                    _product_variant_list.remove(record_id)
                raise ValidationError(
                    _("A Product should be 'Can be Sold' and 'Can be Purchased' before updation"))
