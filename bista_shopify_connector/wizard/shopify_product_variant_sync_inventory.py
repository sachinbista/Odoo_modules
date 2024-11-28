##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from .. import shopify
import time
from odoo import models


class ShopifyVariantInventorySync(models.TransientModel):
    _name = 'shopify.variant.inventory.sync'
    _description = 'Export Shopify Product Inventory'

    def shopify_product_variant_inventory_sync(self):
        """
            This method is used for inventory sync for product
            variants from odoo to shopify.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        shopify_prod_obj = self.env['shopify.product.product']
        stock_quant_obj = self.env['stock.quant'].sudo()
        location_env = self.env['stock.location'].sudo()
        for rec in self:
            active_ids = rec._context.get('active_ids')
            shopify_prod_search = shopify_prod_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_product_id", "not in", ['', False]),
                 ('update_shopify_inv', '=', True)])
            # Add counter b'coz we can send only 2 request per second
            count = 1
            for prod in shopify_prod_search:
                inventory_item_id = prod.shopify_inventory_item_id
                shopify_config_id = prod.shopify_config_id.id
                prod.shopify_config_id.check_connection()
                shopify_locations_records = location_env.sudo().search(
                    [('shopify_config_id', '=', shopify_config_id)])
                for location_rec in shopify_locations_records:
                    shopify_location = location_rec.shopify_location_id
                    # shopify_location_id = location_rec.id
                    available_qty = 0
                    quant_locations = stock_quant_obj.sudo().search(
                        [('location_id.usage', '=', 'internal'),
                         ('product_id', '=', prod.product_variant_id.id),
                         ('location_id.shopify_location_id', '=',
                          shopify_location)])
                    for quant_location in quant_locations:
                        available_qty += quant_location.quantity
                    if available_qty and not location_rec.shopify_legacy:
                        location = shopify.InventoryLevel.set(
                            shopify_location,
                            inventory_item_id,
                            int(available_qty))
                if count % 2 == 0:
                    time.sleep(0.5)
                count += 1
