##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def prepare_shopify_fulfillment_line_vals_for_kit_products(self, picking_id, product_moves, line_items_dict):
        bom_product_moves = picking_id.move_ids_without_package.filtered(
            lambda x: x.id not in product_moves.ids and x.sale_line_id and
                      x.bom_line_id and x.bom_line_id.bom_id.type == 'phantom')
        if bom_product_moves:
            sale_order_lines = bom_product_moves.mapped('sale_line_id')
            for sol in sale_order_lines:
                new_fillment_qty = sol.qty_delivered - sol.shopify_fulfilled_qty
                bom_move = bom_product_moves.filtered(lambda m: m.sale_line_id.id == sol.id)
                if new_fillment_qty > 0:
                    fulfillment_line_id = bom_move.shopify_fulfillment_line_id
                    assigned_location_id = bom_move.shopify_assigned_location_id

                    if line_items_dict.get(bom_move.shopify_fulfillment_order_id):
                        line_items_dict[bom_move.shopify_fulfillment_order_id].append({"id": fulfillment_line_id,
                                                                                       "quantity": int(new_fillment_qty),
                                                                                       "assigned_location_id": assigned_location_id})
                    else:
                        line_items_dict.update({
                            bom_move.shopify_fulfillment_order_id: [{"id": fulfillment_line_id,
                                                                     "quantity": int(new_fillment_qty),
                                                                     "assigned_location_id": assigned_location_id}]})
                sol.write({'shopify_fulfilled_qty': sol.shopify_fulfilled_qty + new_fillment_qty})
        return line_items_dict

    def process_picking_for_kit_products(self, picking_id, move_ids, qty_done, product_id):
        phantom_move_ids = picking_id.move_ids_without_package.filtered(
            lambda r: r.id not in move_ids.ids)
        for move in phantom_move_ids:
            update_qty = 0.00
            if move.quantity and qty_done <= move.quantity:
                update_qty = qty_done
            elif move.quantity > 0:
                update_qty = move.quantity
            if update_qty > 0:
                if qty_done > move.quantity:
                    raise UserError(
                        _("Please update quantity of '%s' on '%s' to "
                          "process the order '%s'!. '%s' is the kit "
                          "component.") % (product_id.name, picking_id.sale_id.name, product_id.name))
            else:
                raise UserError(
                    _("Please update quantity of '%s' on '%s' to process "
                      "the order '%s'! '%s' is the kit component") %
                    (product_id.name, picking_id.location_id.complete_name,
                     picking_id.sale_id.name, product_id.name))
