##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from .. import shopify
import time
from odoo import models, _
from datetime import datetime, timedelta


class ShopifyVariantInventorySync(models.TransientModel):
    _name = 'shopify.variant.inventory.sync'
    _description = 'Export Shopify Product Inventory'

    def get_available_qty(self, odoo_location, product, shopify_prod_search):
        available_qty = self.env['stock.quant']._get_quantity_with_child_locations(
            odoo_location, product)
        return available_qty

    def shopify_product_variant_inventory_sync(self):
        shopify_prod_obj = self.env['shopify.product.product']
        stock_quant_obj = self.env['stock.quant']
        location_mapp_env = self.env['shopify.location.mapping']
        shopify_log_line_obj = self.env['shopify.log.line']
        for rec in self:
            active_ids = rec._context.get('active_ids')
            shopify_prod_search = shopify_prod_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_product_id", "not in", ['', False]),
                 ('update_shopify_inv', '=', True)])
            if shopify_prod_search:
                shopify_prod_search |= shopify_prod_obj.search(
                    [('product_variant_id', 'in',shopify_prod_search.mapped('product_variant_id.id')),
                     ("shopify_product_id", "not in", ['', False]),
                     ('update_shopify_inv', '=', True),
                     ('id','not in',shopify_prod_search.ids)])
            # Add counter b'coz we can send only 2 request per second
            # count = 1
            seconds = 10
            shopify_log_line_obj = self.env['shopify.log.line']
            log_line_vals = {
                'name': "Export Stock",
                'operation_type': 'export_stock',
            }
            parent_log_line_id = False
            shopify_initial_id = False
            for prod in shopify_prod_search:
                inventory_item_id = prod.shopify_inventory_item_id
                shopify_config_id = prod.shopify_config_id
                if shopify_config_id != shopify_initial_id:
                    shopify_initial_id = shopify_config_id
                    log_line_vals.update({
                        'shopify_config_id': shopify_initial_id.id,
                    })
                    parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                prod.shopify_config_id.check_connection()
                shopify_locations_records = location_mapp_env.sudo().search([
                    ('shopify_location_id', '!=', False),
                    ('shopify_config_id', '=', shopify_config_id.id),
                    ('odoo_location_id', '!=', False)])
                # shopify_locations_records = location_mapp_env.sudo().search(
                #     [('shopify_config_id', '=', shopify_config_id)])
                for location_rec in shopify_locations_records:
                    shopify_location = location_rec.shopify_location_id
                    odoo_location = location_rec.odoo_location_id
                    # shopify_location_id = location_rec.id
                    # available_qty = 0
                    # all_locations = self.env['stock.location'].search([('id', 'child_of', odoo_location.id)]).ids
                    # quant_locations = stock_quant_obj.sudo().search(
                    #     [
                    #         ('location_id', 'in', all_locations),
                    #         ('location_id.usage', '=', 'internal'),
                    #         ('product_id', '=', prod.product_variant_id.id),
                    #     ])
                    # for quant_location in quant_locations:
                    #     available_qty += quant_location.quantity
                    available_qty = self.get_available_qty(odoo_location, prod.product_variant_id, shopify_prod_search)
                    # available_qty = self.env['stock.quant']._get_quantity_with_child_locations(
                    #     odoo_location, prod.product_variant_id),
                    # if available_qty and not location_rec.shopify_legacy:
                    if not location_rec.shopify_legacy:
                        name = "%s - %s" % (location_rec.odoo_location_id.display_name,
                                            prod.product_variant_id.display_name)
                        job_descr = _("Export Stock to shopify: %s") % (name and name.strip())

                        log_line_id = shopify_log_line_obj.create({
                            'name': job_descr,
                            'shopify_config_id': shopify_config_id.id,
                            'id_shopify': f"Location: {location_rec.shopify_location_id or ''} Product: {prod.shopify_product_id}",
                            'operation_type': 'export_stock',
                            'parent_id': parent_log_line_id.id
                        })
                        eta = datetime.now() + timedelta(seconds=seconds)
                        prod.shopify_config_id.with_delay(description=job_descr, max_retries=5, eta=eta).export_stock(
                            location_rec.shopify_location_id,
                            prod,
                            int(available_qty), log_line_id)
                        # shopify.InventoryLevel.set(
                        #     shopify_location,
                        #     inventory_item_id,
                        #     int(available_qty))
                        seconds += 2
                if parent_log_line_id:
                    parent_log_line_id.update({
                        'state': 'success',
                        'message': 'Operation Successful'
                    })
                # if count % 2 == 0:
                #     time.sleep(0.5)
                # count += 1
