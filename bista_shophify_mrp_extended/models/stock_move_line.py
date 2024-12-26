##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import logging
from odoo import models, fields, api, _
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def phantom_product_stock_update(self):
        '''Method to update the stock for phantom products'''
        shopify_log_line_obj = self.env['shopify.log.line']
        error_log_env = self.env['shopify.error.log']
        shopify_prod_obj = self.env['shopify.product.product']
        seconds = 10
        shopify_initial_id = False
        parent_log_line_id = False

        log_line_vals = {
            'name': "Export Stock",
            'operation_type': 'export_stock',
        }

        bom_line_ids = self.filtered(
            lambda m: m.move_id.bom_line_id and
                      m.move_id.bom_line_id.bom_id.type == 'phantom').mapped('move_id.bom_line_id')

        if not bom_line_ids:
            bom_line_ids |= self.env[
                'mrp.bom.line'].search([
                ('product_id', 'in', self.mapped('product_id').ids),
                ('bom_id.type', '=', 'phantom')])

        source_loc_ids = self.mapped('location_id')
        destination_loc_ids = self.mapped('location_dest_id')
        product_ids = self.env['product.product']
        for bline in bom_line_ids:
            if bline.bom_id.product_id:
                product_ids |= bline.bom_id.product_id
            if (not bline.bom_id.product_id and
                    bline.bom_id.product_tmpl_id):
                product_ids |= bline.bom_id.product_tmpl_id.product_variant_ids

        shopify_log_id = False
        for product_id in product_ids:
            for source_loc_id in source_loc_ids:
                location_id = self.env['stock.move']._check_if_child_location(
                    source_loc_id)
                location_mapping_ids = self.env['shopify.location.mapping'].search([
                    ('odoo_location_id', '=', location_id.id),
                    ('shopify_config_id.active', '=', True)
                ])
                shopify_location_recs = location_mapping_ids
                for shopify_location_rec in shopify_location_recs:
                    shopify_config_rec = shopify_location_rec.shopify_config_id
                    shopify_location_id = shopify_location_rec.shopify_location_id
                    if not shopify_log_id:
                        shopify_log_id = error_log_env.create_update_log(
                            shopify_config_id=shopify_config_rec,
                            operation_type='export_stock')
                    shopify_product1 = shopify_prod_obj.with_user(
                        self.env.user).search([
                        ('product_variant_id', '=', product_id.id),
                        ('shopify_config_id', '=',
                         shopify_config_rec.id)], limit=1)
                    inventory_item_id = \
                        shopify_product1.shopify_inventory_item_id
                    # shopify_product_cost = product_rec.standard_price
                    if inventory_item_id and \
                            shopify_product1.update_shopify_inv:
                        name = "%s - %s" % (
                            shopify_location_rec.odoo_location_id.display_name,
                            shopify_product1.product_variant_id.display_name)
                        job_descr = _(
                            "Done Export Kit Product Stock to shopify: %s") % (
                                            name and name.strip())
                        if shopify_initial_id != shopify_config_rec:
                            shopify_initial_id = shopify_config_rec
                            log_line_vals.update({
                                'shopify_config_id': shopify_config_rec.id,
                            })
                            parent_log_line_id = shopify_log_line_obj.create(
                                log_line_vals)

                        log_line_id = (
                            shopify_log_line_obj.create(
                                {
                                    'name': job_descr,
                                    'shopify_config_id': shopify_config_rec.id,
                                    'id_shopify': f"Location: "
                                                  f"{shopify_location_rec.shopify_location_id or ''} Product: {shopify_product1.shopify_product_id}",
                                    'operation_type': 'export_stock',
                                    'parent_id': parent_log_line_id.id
                                }))

                        available_qty = shopify_product1.product_variant_id.with_context(
                            {'location': location_id.id}
                        )._compute_quantities_dict(
                            lot_id=False,
                            owner_id=False,
                            package_id=False)
                        if available_qty:
                            available_qty = available_qty.get(
                                shopify_product1.product_variant_id.id).get(
                                'free_qty', 0.0) or 0.0
                        eta = datetime.now() + timedelta(
                            seconds=seconds)
                        shopify_config_rec.with_user(
                            self.env.user).with_delay(
                            description=job_descr,
                            max_retries=5,
                            eta=eta).update_shopify_inventory(
                            shopify_location_id,
                            inventory_item_id,
                            int(available_qty) or 0, log_line_id)
                        seconds += 1
                        if parent_log_line_id:
                            parent_log_line_id.update({
                                'state': 'success',
                                'message': 'Operation Successful'
                            })

            # destination location process
            for destination_loc_id in destination_loc_ids:
                location_dest_id = self.env[
                    'stock.move']._check_if_child_location(
                    destination_loc_id)

                location_dest_mapping_ids = self.env[
                    'shopify.location.mapping'].search([
                    ('odoo_location_id', '=',
                     location_dest_id.id),
                    ('shopify_config_id.active', '=', True)])
                shopify_location_recs = location_dest_mapping_ids
                for shopify_location_rec in shopify_location_recs:
                    shopify_config_rec = shopify_location_rec.shopify_config_id
                    shopify_location_id = shopify_location_rec.shopify_location_id
                    if not shopify_log_id:
                        shopify_log_id = error_log_env.create_update_log(
                            shopify_config_id=shopify_config_rec,
                            operation_type='export_stock')
                    shopify_product1 = shopify_prod_obj.with_user(
                        self.env.user).search([
                        ('product_variant_id', '=', product_id.id),
                        ('shopify_config_id', '=',
                         shopify_config_rec.id)], limit=1)
                    inventory_item_id = \
                        shopify_product1.shopify_inventory_item_id
                    # shopify_product_cost = product_rec.standard_price
                    if inventory_item_id and \
                            shopify_product1.update_shopify_inv:
                        name = "%s - %s" % (
                            shopify_location_rec.odoo_location_id.display_name,
                            shopify_product1.product_variant_id.display_name)
                        job_descr = (_(
                            "Done dest Export Kit Product Stock to shopify: %s")
                                     % (
                                            name and name.strip()))

                        if (shopify_initial_id != shopify_config_rec) or (
                                not parent_log_line_id) or (
                                        parent_log_line_id and
                                        parent_log_line_id.shopify_config_id.id != shopify_config_rec.id):
                            shopify_initial_id = shopify_config_rec
                            log_line_vals.update({
                                'shopify_config_id': shopify_config_rec.id,
                            })
                            parent_log_line_id = shopify_log_line_obj.create(
                                log_line_vals)
                        log_line_id = (
                            shopify_log_line_obj.create(
                                {
                                    'name': job_descr,
                                    'shopify_config_id': shopify_config_rec.id,
                                    'id_shopify': f"Location: "
                                                  f"{shopify_location_rec.shopify_location_id or ''} Product: {shopify_product1.shopify_product_id}",
                                    'operation_type': 'export_stock',
                                    'parent_id': parent_log_line_id.id
                                }))

                        available_qty = shopify_product1.product_variant_id.with_context(
                            {'location': location_dest_id.id}
                        )._compute_quantities_dict(
                            lot_id=False,
                            owner_id=False,
                            package_id=False)
                        if available_qty:
                            available_qty = available_qty.get(
                                shopify_product1.product_variant_id.id).get(
                                'free_qty', 0.0) or 0.0

                        eta = datetime.now() + timedelta(
                            seconds=seconds)
                        shopify_config_rec.with_user(
                            self.env.user).with_delay(
                            description=job_descr,
                            max_retries=5,
                            eta=eta).update_shopify_inventory(
                            shopify_location_id,
                            inventory_item_id,
                            int(available_qty) or 0.0, log_line_id)
                        seconds += 2
                    if parent_log_line_id:
                        parent_log_line_id.update({
                            'state': 'success',
                            'message': 'Operation Successful'
                        })

    def phantom_product_stock_update_for_kit_products(self):
        res = super(StockMoveLine, self).phantom_product_stock_update_for_kit_products()
        self.phantom_product_stock_update()
        return res
