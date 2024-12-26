##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import logging
from odoo import models, fields, api, _
import requests
import json
import traceback

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _do_unreserve_phantom_product(self):
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Export Stock",
            'operation_type': 'export_stock',
        }
        parent_log_line_id = False
        shopify_initial_id = False

        for move in self:
            shopify_prod_obj = self.env['shopify.product.product']
            product_ids = self.env['product.product']
            try:
                location_id = self._check_if_child_location(
                    move.location_id)
                location_mapping_ids = self.env[
                    'shopify.location.mapping'].search([
                    ('odoo_location_id', '=', location_id.id),
                    ('shopify_config_id.active', '=', True)])
                shopify_location_recs = location_mapping_ids
                for shopify_location_rec in shopify_location_recs:
                    if shopify_location_rec:
                        shopify_config_rec = shopify_location_rec.shopify_config_id
                        shopify_location_id = shopify_location_rec.shopify_location_id
                        bom_line_ids = move.filtered(
                            lambda m: m.bom_line_id
                                      and m.bom_line_id.bom_id.type == 'phantom').mapped(
                            'bom_line_id')

                        bom_line_ids |= self.env[
                            'mrp.bom.line'].search([(
                            'product_id', '=', move.product_id.id),
                            ('bom_id.type', '=', 'phantom')])

                        for bline in bom_line_ids:
                            if bline.bom_id.product_id:
                                product_ids |= bline.bom_id.product_id
                            if (not bline.bom_id.product_id and
                                    bline.bom_id.product_tmpl_id):
                                product_ids |= bline.bom_id.product_tmpl_id.product_variant_ids
                        for product_id in product_ids:
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
                                if shopify_config_rec != shopify_initial_id:
                                    shopify_initial_id = shopify_config_rec
                                    log_line_vals.update({
                                        'shopify_config_id': shopify_config_rec.id,
                                    })
                                    parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                                job_descr = (_(
                                    "unreserve Export Kit Product Stock to "
                                    "shopify: %s")
                                             % (name and name.strip()))
                                log_line_id = shopify_log_line_obj.create(
                                    {
                                        'name': job_descr,
                                        'shopify_config_id': shopify_config_rec.id,
                                        'id_shopify': f"Location: "
                                                      f"{shopify_location_rec.shopify_location_id or ''} Inventory: {shopify_product1.shopify_inventory_item_id}",
                                        'operation_type': 'export_stock',
                                        'parent_id': parent_log_line_id.id
                                    })
                                available_qty = shopify_product1.product_variant_id.with_context(
                                    {'location': shopify_location_rec.odoo_location_id.id}
                                )._compute_quantities_dict(
                                    lot_id=False,
                                    owner_id=False,
                                    package_id=False)
                                if available_qty:
                                    available_qty = available_qty.get(
                                        shopify_product1.product_variant_id.id).get(
                                        'free_qty', 0.0) or 0.0

                                shopify_config_rec.with_user(
                                    self.env.user).with_delay(
                                    description=job_descr,
                                    max_retries=5).update_shopify_inventory(
                                    shopify_location_id, inventory_item_id,
                                    int(available_qty), log_line_id)
                    if parent_log_line_id:
                        parent_log_line_id.update({
                            'state': 'success',
                            'message': 'Operation Successful'
                        })
            except Exception as e:
                parent_log_line_id.update({
                    'state': 'error',
                    'message': traceback.format_exc(),
                })

    def _update_phantom_reserved_quantity(self):
        '''Method to update latest quantity of phantom products after
        reservation'''
        log_line_vals = {
            'name': "Export Stock",
            'operation_type': 'export_stock',
        }
        parent_log_line_id = False

        shopify_initial_id = False
        shopify_prod_obj = self.env['shopify.product.product']
        error_log_env = self.env['shopify.error.log']
        shopify_log_line_obj = self.env['shopify.log.line']
        product_ids = self.env['product.product']

        for move in self:
            bom_line_ids = move.filtered(
                lambda m: m.bom_line_id and m.bom_line_id.bom_id.type ==
                          'phantom').mapped('bom_line_id')

            bom_line_ids |= self.env[
                'mrp.bom.line'].search([
                ('product_id', '=', move.product_id.id),
                ('bom_id.type', '=', 'phantom')])

            for bline in bom_line_ids:
                if bline.bom_id.product_id:
                    product_ids |= bline.bom_id.product_id
                if (not bline.bom_id.product_id and
                        bline.bom_id.product_tmpl_id):
                    product_ids |= bline.bom_id.product_tmpl_id.product_variant_ids
        try:
            location_id = move._check_if_child_location(move.location_id)
            location_mapping_ids = self.env[
                'shopify.location.mapping'].search([
                ('odoo_location_id', '=', location_id.id),
                ('shopify_config_id.active', '=', True)])
            shopify_location_recs = location_mapping_ids
            for shopify_location_rec in shopify_location_recs:
                if shopify_location_rec:
                    # and shopify_location_rec.shopify_config_id.sync_inventory_on_reservation):
                    shopify_config_rec = shopify_location_rec.shopify_config_id
                    if shopify_config_rec != shopify_initial_id:
                        shopify_initial_id = shopify_config_rec
                        log_line_vals.update({
                            'shopify_config_id': shopify_config_rec.id,
                        })
                        parent_log_line_id = shopify_log_line_obj.create(
                            log_line_vals)
                    shopify_location_id = shopify_location_rec.shopify_location_id
                    error_log_env.create_update_log(
                        shopify_config_id=shopify_config_rec,
                        operation_type='export_stock')
                    for product_id in product_ids:
                        if product_id:
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
                                    "reserve Export Kit Product Stock to "
                                    "shopify: %s")
                                             % (name and name.strip()))
                                log_line_id = shopify_log_line_obj.create(
                                    {
                                        'name': job_descr,
                                        'shopify_config_id': shopify_config_rec.id,
                                        'id_shopify': f"Location: "
                                                      f"{shopify_location_rec.shopify_location_id or ''} Product: {shopify_product1.shopify_product_id}",
                                        'operation_type': 'export_stock',
                                        'parent_id': parent_log_line_id.id
                                    })
                                available_qty = shopify_product1.product_variant_id.with_context(
                                    {'location': shopify_location_rec.odoo_location_id.id}
                                )._compute_quantities_dict(
                                    lot_id=False,
                                    owner_id=False,
                                    package_id=False)
                                if available_qty:
                                    available_qty = available_qty.get(
                                        shopify_product1.product_variant_id.id).get(
                                        'free_qty', 0.0) or 0.0

                                shopify_config_rec.with_user(
                                    self.env.user).with_delay(
                                    description=job_descr,
                                    max_retries=5).update_shopify_inventory(
                                    shopify_location_id, inventory_item_id,
                                    int(available_qty), log_line_id)
                if parent_log_line_id:
                    parent_log_line_id.update({
                        'state': 'success',
                        'message': 'Operation Successful'
                    })
        except Exception as e:
            if parent_log_line_id:
                parent_log_line_id.update({
                    'state': 'error',
                    'message': traceback.format_exc(),
                })

    def _do_unreserve_phantom_product_for_kit_products(self):
        res = super(StockMove, self)._do_unreserve_phantom_product_for_kit_products()
        self._do_unreserve_phantom_product()
        return res

    def _update_phantom_reserved_quantity_for_kit_products(self):
        res = super(StockMove, self)._update_phantom_reserved_quantity_for_kit_products()
        self._update_phantom_reserved_quantity()
        return res
