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
        shopify_prod_obj = self.env['shopify.product.product']
        stock_quant_obj = self.env['stock.quant']
        location_env = self.env['stock.location']
        for rec in self:
            active_ids = rec._context.get('active_ids')
            shopify_prod_search = shopify_prod_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_product_id", "not in", ['', False]),
                 ('update_shopify_inv', '=', True)])

            # Add counter b'coz we can send only 2 request per second
            count = 1
            for prod in shopify_prod_search:
                shopify_config = prod.shopify_config_id
                shopify_config.sudo().check_connection()
                inventory_item_id = prod.shopify_inventory_item_id
                shopify_config_id = prod.shopify_config_id.id
                shopify_locations_records = location_env.sudo().search(
                    [('shopify_config_id', '=', shopify_config.id), ('usage', '=', 'view'),
                     ('shopify_location_id', '!=', False)])
                f_qty = 0.0
                sh_location = ''
                sh_inv_item = ''
                for location_rec in shopify_locations_records:
                    shopify_location = location_rec.shopify_location_id
                    # shopify_location_id = location_rec.id
                    product_variant_id = prod.product_variant_id
                    qty_available = product_variant_id.with_context(
                        {'location': location_rec.id})._compute_quantities_dict(self._context.get('lot_id'),
                                                                               self._context.get('owner_id'),
                                                                               self._context.get('package_id'))
                    variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
                    shopify_location_id = location_rec.shopify_location_id
                    shopify_inventory_item_id = prod.shopify_inventory_item_id
                    f_qty += variant_qty
                    sh_location = shopify_location_id
                    sh_inv_item = shopify_inventory_item_id
                    shopify.InventoryLevel.set(sh_location,
                                               sh_inv_item,
                                               int(f_qty))
                    product_variant_id.is_shopify_qty_changed = False

                    # available_qty = 0
                    # quant_locations = stock_quant_obj.sudo().search(
                    #     [('location_id.usage', '=', 'internal'),
                    #      ('product_id', '=', prod.product_variant_id.id),
                    #      ('location_id.shopify_location_id', '=',
                    #       shopify_location)])
                    # for quant_location in quant_locations:
                    #     available_qty += quant_location.quantity
                    # if available_qty and not location_rec.shopify_legacy:
                    #     location = shopify.InventoryLevel.set(
                    #         shopify_location,
                    #         inventory_item_id,
                    #         int(available_qty))
                if count % 2 == 0:
                    time.sleep(0.5)
                count += 1
