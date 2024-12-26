# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    weight = fields.Float(related="product_id.weight")
    product_length = fields.Float(related="product_id.product_length")
    product_width = fields.Float(related="product_id.product_width")
    product_height = fields.Float(related="product_id.product_height")

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        product_warehouse_qty_obj = self.env['product.warehouse.quantity']
        if go_flow_instance_obj:
            warehouses = res.mapped('warehouse_id')
            goflow_warehouse = self.env['goflow.warehouse'].search(
                [('warehouse_id', 'in', warehouses.ids)])
            for warehouse in goflow_warehouse.filtered(lambda x: x.is_sync_goflow_inventory):
                lines = []
                goflow_products = self.env['goflow.product'].search([('product_id', 'in', res.mapped('product_id').ids)])
                product_dict = {product.product_id.id: product.product_external_id for product in goflow_products}
                for rec in res.filtered(lambda x: x.warehouse_id.id == warehouse.warehouse_id.id):
                    move_orig_ids = False
                    if rec.picking_id.picking_type_code == 'incoming' and rec.picking_id.purchase_id:
                        product_external_id = False
                        product_external_id = product_dict.get(rec.product_id.id, False)
                        if rec.product_id.id in product_dict:
                            warehouse_id = warehouse.warehouse_id
                            product_warehouse_qty = product_warehouse_qty_obj.search(
                                [('product_id', '=', rec.product_id.id), ('warehouse_id', '=', warehouse_id.id)])
                            on_hand_quantity = rec.product_id.with_context(warehouse=warehouse_id.id).qty_available
                            goflow_product = self.env['goflow.product'].search([('product_id', '=', rec.product_id.id)],
                                                                               limit=1)
                            goflow_sync = False
                            if goflow_product:
                                goflow_sync = True
                            if product_warehouse_qty:
                                product_warehouse_qty.write({
                                    'on_hand_quantity': on_hand_quantity,
                                    'goflow_sync': goflow_sync
                                })
                            else:
                                product_warehouse_qty_obj.create({
                                    'product_id': rec.product_id.id,
                                    'warehouse_id': warehouse_id.id,
                                    'on_hand_quantity': on_hand_quantity,
                                    'goflow_sync': goflow_sync
                                })

                            # product_external_id = product_dict.get(rec.product_id.id, False)
                        # if product_external_id:
                        #     lines.append({
                        #         "product_id": int(product_external_id),
                        #         "quantity": int(rec.product_id.with_context(warehouse=rec.warehouse_id.id).qty_available),
                        #         "cost": float(rec.price_unit) if rec.price_unit
                        #         else float(rec.product_id.standard_price),
                        #         "reason": "Purchase Inventory Adjustment created from Odoo"
                        #     })
                            # ref += rec.display_name
                    elif rec.picking_id.picking_type_code == 'outgoing' and rec.picking_id and rec.picking_id.external_origin == 'go_flow':
                        warehouse_id = rec.location_id.warehouse_id
                        product_warehouse_qty = product_warehouse_qty_obj.search(
                            [('product_id', '=', rec.product_id.id), ('warehouse_id', '=', warehouse_id.id)])
                        on_hand_quantity = rec.product_id.with_context(warehouse=warehouse_id.id).qty_available
                        goflow_product = self.env['goflow.product'].search([('product_id', '=', rec.product_id.id)],
                                                                           limit=1)
                        goflow_sync = False
                        if goflow_product:
                            goflow_sync = True
                        if product_warehouse_qty:
                            product_warehouse_qty.write({
                                'on_hand_quantity': on_hand_quantity,
                                'goflow_sync': goflow_sync
                            })
                        else:
                            product_warehouse_qty_obj.create({
                                'product_id': rec.product_id.id,
                                'warehouse_id': rec.location_id.warehouse_id.id,
                                'on_hand_quantity': on_hand_quantity,
                                'goflow_sync': goflow_sync
                            })

                #         if rec.product_id.id in product_dict:
                #             product_external_id = product_dict.get(rec.product_id.id, False)
                #         if product_external_id:
                #             lines.append({
                #                 "product_id": int(product_external_id),
                #                 "quantity": int(rec.product_id.with_context(warehouse=rec.warehouse_id.id).qty_available),
                #                 "cost": float(rec.price_unit) if rec.price_unit else float(rec.product_id.standard_price),
                #                 "reason": "Delivery order validated from Odoo"
                #             })
                #
                # data = {
                #     "type": "absolute",
                #     "warehouse_id": str(warehouse.goflow_warehouse_id),
                #     "reference_number": '',
                #     "lines": lines
                # }
                # if lines:
                #     go_flow_instance_obj._send_goflow_request('post', '/v1/inventory/adjustments', payload=data)
                # print(response)
        return res


