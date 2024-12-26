##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .. import shopify
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"

    shopify_product_product_ids = fields.One2many(
        "shopify.product.product",
        "product_variant_id",
        "Shopify Product Variants",
        help="Enter Shopify Product Variants")
    shopify_shipping_product = fields.Boolean(
        "Is Shopify Shipping Product",
        help="Use this product as shipping product while import order?",
        tracking=True)
    shopify_discount_product = fields.Boolean(
        "Is Shopify Discount Product",
        help="Use this product as discount product while import order?",
        tracking=True)
    is_gift_card = fields.Boolean("Is Gift Card?")
    shopify_name = fields.Char("Shopify Name")
    lst_price = fields.Float(
        'Sales Price', compute=False,
        digits='Product Price', inverse=False,
        help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.")

    def update_shopify_old_stock(self):
        """"Method to move stock from old product to new product"""
        # products = self.env['product.product'].search(
        #     [('default_code', 'ilike', '-MAGENTO-OLD'), ('active', '=', False)])
        product_with_issue = []
        count = len(self.ids)
        for prod in self:
            _logger.info("\n\n--------count %s" % count)
            try:
                _logger.info("\n\n-----------prod %s" % prod)
                old_internal_ref = prod.default_code
                parts = old_internal_ref.split("-MAGENTO-OLD")
                new_product_id = self.search(
                    [('default_code', '=', parts[0])])
                if new_product_id:
                    new_product_id.update({
                        'standard_price': prod.standard_price,
                        'weight': prod.weight
                    })
                    quants = self.env['stock.quant'].search([
                        ('product_id', '=', prod.id),
                        ('location_id.usage', '=', 'internal')
                    ])
                    _logger.info("\n\n-----------quants %s" % quants)
                    if quants:
                        for quant in quants:
                            _logger.info("\n\n-----------quant %s" % quant)
                            new_quants = quant.copy(
                                default={'product_id': new_product_id.id,
                                         'quantity': 0,
                                         'inventory_quantity': quant.quantity,
                                         'inventory_quantity_set': True,
                                         'reserved_quantity': 0})
                            quant.write({'inventory_quantity': 0,
                                         'inventory_quantity_set': True})
                            quant.action_apply_inventory()
                            new_quants.action_apply_inventory()
                count = count - 1
            except Exception as e:
                _logger.info("\n\n---------e %s" % (str(e)))
                product_with_issue.append(prod.id)
        _logger.info(
            "\n\n----------product_with_issue %s" % product_with_issue)

    def open_shopify_variant(self):
        return {
            'name': _('Shopify Product Variant'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'shopify.product.product',
            'context': self.env.context,
            'domain': [('id', 'in', self.shopify_product_product_ids and
                        self.shopify_product_product_ids.ids or [])]
        }

    @api.constrains('default_code')
    def _check_default_code_uniq_product(self):
        """
        Prevent the default code duplication when creating product variant
        """
        for rec in self:
            if rec.default_code:
                search_product_count = self.search_count(
                    [('default_code', '=', rec.default_code)])
                if search_product_count > 1:
                    raise ValidationError(
                        _('Default Code must be unique per Product!'))
        return True

    @api.model
    def create(self, vals):
        """
        Restrict a user from creating multiple shipping products and multiple
        discount products for Shopify.
        """
        res = super(ProductProduct, self).create(vals)
        shopify_shipping_product = vals.get('shopify_shipping_product') or \
            self.shopify_shipping_product
        shopify_discount_product = vals.get('shopify_discount_product') or \
            self.shopify_discount_product
        if shopify_shipping_product:
            shipping_product_variant_count = self.search_count(
                [('type', '=', 'service'),
                 ('shopify_shipping_product', '=', True)])
            if shipping_product_variant_count > 1:
                raise ValidationError(_("Shipping Product Already Exists in "
                                        "the system !"))
        if shopify_discount_product:
            discount_product_variant_count = self.search_count(
                [('type', '=', 'service'),
                 ('shopify_discount_product', '=', True)])
            if discount_product_variant_count > 1:
                raise ValidationError(_("Discount Product Already Exists in "
                                        "the system !"))
        return res

    def write(self, vals):
        if not self._context.get('job_uuid'):
            for rec in self:
                for shopify_product_variant in rec.shopify_product_product_ids:
                    if any(field in vals for field in (
                            'lst_price', 'standard_price', 'default_code',
                            'barcode', 'image_1920', 'weight')):
                        shopify_product_variant.write({
                            'variant_ready_for_update': True
                        })
                        shopify_product_variant.shopify_product_template_id.write({
                            'ready_to_update': True
                        })
        if self._context.get('job_uuid') and self._context.get(
                'from_shopify_import') and self._context.get('shopify_config_id')\
                and 'active' in vals and vals.get('active') == False:
            for product in self:
                shopify_product_id = (
                    product.shopify_product_product_ids.filtered(
                        lambda p: p.shopify_config_id and
                                  p.shopify_config_id.id == self._context[
                                      'shopify_config_id'].id))
                vals.update({'default_code': str(product.default_code) + '-MAGENTO-OLD'})
                if product.barcode:
                    vals.update({
                        'barcode': product.barcode + '-MAGENTO-OLD' if product.barcode else '',

                    })
                shopify_product_id.unlink()
        res = super(ProductProduct, self).write(vals)

        """
        Restrict a user from creating multiple shipping products and multiple
        discount products for Shopify.
        """
        for rec in self:
            shopify_shipping_product = vals.get('shopify_shipping_product') or \
                rec.shopify_shipping_product
            shopify_discount_product = vals.get('shopify_discount_product') or \
                rec.shopify_discount_product
            if shopify_shipping_product:
                shipping_product_variant_count = self.search_count(
                    [('type', '=', 'service'),
                     ('shopify_shipping_product', '=', True)])
                if shipping_product_variant_count > 1:
                    raise ValidationError(_("Shipping Product Already Exists in "
                                            "the system !"))
            if shopify_discount_product:
                discount_product_variant_count = self.search_count(
                    [('type', '=', 'service'),
                     ('shopify_discount_product', '=', True)])
                if discount_product_variant_count > 1:
                    raise ValidationError(_("Discount Product Already Exists in "
                                            "the system !"))
        return res

    def unlink(self):
        if self._context.get('job_uuid') and self._context.get(
                'from_shopify_import') and self._context.get('shopify_config_id'):
            for product in self:
                shopify_product_id = (
                    product.shopify_product_product_ids.filtered(
                        lambda p: p.shopify_config_id and
                                  p.shopify_config_id.id == self._context[
                                      'shopify_config_id'].id))
                shopify_product_id.unlink()
        # else:
        #     shopify_log_line_obj = self.env['shopify.log.line']
        #     for product in self:
        #         seconds = 30
        #         for shop_prod in product.shopify_product_product_ids:
        #             eta = datetime.now() + timedelta(seconds=seconds)
        #             name = product.display_name or ''
        #             job_descr = _("Delete Produc from Shopifyt:   %s") % (
        #                     name and name.strip())
        #             log_line_id = shopify_log_line_obj.create({
        #                 'message': job_descr,
        #                 'shopify_config_id': shop_prod.shopify_config_id.id,
        #                 'id_shopify': shop_prod.shopify_product_id or '',
        #                 'operation_type': 'delete_product',
        #             })
        #             shop_prod.with_delay(
        #                     description=job_descr, max_retries=5,
        #                     eta=eta).remove_variant_from_shopify(
        #                 shop_prod.shopify_config_id, log_line_id)
        #         seconds += 2
                # shopify_product_id.unlink()
            # shopify.Product().delete(shopify_tmpl_id)
        return super(ProductProduct, self).unlink()
        