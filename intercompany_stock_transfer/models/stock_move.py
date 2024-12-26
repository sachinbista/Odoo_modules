# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby

import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_inter_warehouse_transfer_assign(self, line):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `reserved_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """
        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.reserved_availability for move in self}
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        # Once the quantities are assigned, we want to find a better destination location thanks
        # to the putaway rules. This redirection will be applied on moves of `moves_to_redirect`.
        moves_to_redirect = OrderedSet()
        moves_to_assign = self

        for move in moves_to_assign:
            rounding = roundings[move]
            if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                assigned_moves_ids.add(move.id)
            elif not move.move_orig_ids:
                if move.procure_method == 'make_to_order':
                    continue
                # If we don't need any quantity, consider the move assigned.
                need = line.product_uom_qty
                if float_is_zero(need, precision_rounding=rounding):
                    assigned_moves_ids.add(move.id)
                    continue
                # Reserve new quants and create move lines accordingly.
                forced_package_id = line.package_quant_id or None
                available_quantity = move._get_available_quantity(line.location_id, package_id=forced_package_id)
                if available_quantity <= 0:
                    continue
                taken_quantity = move._update_reserved_quantity(need, available_quantity, line.location_id,
                                                                package_id=forced_package_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=rounding):
                    continue
                moves_to_redirect.add(move.id)
                if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                    assigned_moves_ids.add(move.id)
                else:
                    partially_available_moves_ids.add(move.id)

            if move.product_id.tracking == 'serial':
                move.next_serial_count = move.product_uom_qty
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})

    def _push_apply(self):
        ctx = dict(self._context)
        if ctx.get('resupply_transfer'):
            new_moves = []
            for move in self:
                if move.move_dest_ids:
                    continue
                domain = [
                    ('location_src_id', '=', move.location_dest_id.id),
                    ('action', 'in', ('push', 'pull_push'))]
                warehouse_id = move.warehouse_id or \
                    move.picking_id.picking_type_id.warehouse_id

                routes = ctx['resupply_transfer']
                if not routes:
                    routes = move.route_ids
                if move.location_dest_id.company_id == self.env.company:
                    rule = self.env['procurement.group']._search_rule(
                        routes, move.product_packaging_id,
                        move.product_id, warehouse_id, domain)
                else:
                    rule = self.sudo().env['procurement.group']._search_rule(
                        routes, move.product_packaging_id,
                        move.product_id, warehouse_id, domain)
                # Make sure it is not returning the return
                if rule and (
                        not move.origin_returned_move_id or
                        move.origin_returned_move_id.location_dest_id.id !=
                        rule.location_id.id):
                    new_move = rule._run_push(move)
                    if new_move:
                        new_moves.append(new_move)
            return self.env['stock.move'].concat(*new_moves)
        else:
            return super(StockMove, self)._push_apply()
