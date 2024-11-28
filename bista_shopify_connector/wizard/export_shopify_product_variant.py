##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
from odoo import models, _
from odoo.exceptions import AccessError, ValidationError


class ShopifyVariantExport(models.TransientModel):
    _name = 'export.shopify.variant'
    _description = 'Export Shopify Product Variant'

    def export_shopify_product_variant(self):
        """
            This method will export odoo product variant
            into shopify.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        shopify_prod_obj = self.env['shopify.product.product']
        for rec in self:
            active_ids = rec._context.get('active_ids')
            shopify_prod_search = shopify_prod_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_product_id", "in", ['', False])])
            # Add counter b'coz we can send only 2 request per second
            count = 1
            for product in shopify_prod_search:
                product.export_shopify_variant()
                if count % 2 == 0:
                    time.sleep(0.5)
                count += 1

    # def update_variant_on_shopify(self):
    #     """
    #         This method is call from the wizard and update the odoo variant into shopify.
    #     """
    #     shopify_prod_obj = self.env['shopify.product.product']
    #     active_ids = self._context.get('active_ids')
    #     shopify_product_ids = shopify_prod_obj.search(
    #         [('id', 'in', active_ids)])
    #     for product in shopify_product_ids:
    #         if not product.shopify_product_id and not product.shopify_inventory_item_id:
    #             raise ValidationError(
    #                 _("Selected Product {} not exist in Shopify, You need to send those items into shopify from odoo. ").format(product.product_variant_id.name))
    #         product.update_multiple_variant_on_shopify()

    def update_product_variant_odoo_to_shopify(self):
        """
            This method is call from the wizard and update the odoo product variant into shopify.
        """
        shopify_prod_obj = self.env['shopify.product.product']
        active_ids = self._context.get('active_ids')
        if self._context.get('active_model') == 'shopify.product.product':
            shopify_product_ids = shopify_prod_obj.search(
                [('id', 'in', active_ids)])
            for product in shopify_product_ids:
                if not product.shopify_product_id and not product.shopify_inventory_item_id:
                    raise ValidationError(
                        _("Selected Product {} not exist in Shopify, You need to send those items into shopify from odoo. ").format(product.product_variant_id.name))
                product.update_shopify_variant()
        else:
            shopify_product_ids = shopify_prod_obj.search(
                [('product_variant_id', 'in', active_ids)])
            for product in shopify_product_ids:
                if not product.shopify_product_id and not product.shopify_inventory_item_id:
                    raise ValidationError(
                        _("Selected Product {} not exist in Shopify, You need to send those items into shopify from odoo. ").format(product.product_variant_id.name))
                product.update_shopify_variant()
