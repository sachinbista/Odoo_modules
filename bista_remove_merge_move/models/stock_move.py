# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _
from collections import defaultdict
from odoo.tools.float_utils import float_compare
from operator import itemgetter
from odoo.tools.misc import groupby
from odoo.fields import Command
from odoo.tools import float_round, float_is_zero
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    """
    Overwritten function to stop moves from merging
    """

    # necessary hook to be able to override move reservation to a restrict lot, owner, pack, location...

    def _merge_moves(self, merge_into=False):
        """ This method will, for each move in `self`, go up in their linked picking and try to
        find in their existing moves a candidate into which we can merge the move.
        :return: Recordset of moves passed to this method. If some of the passed moves were merged
        into another existing one, return this one and not the (now unlinked) original.
        """
        distinct_fields = self._prepare_merge_moves_distinct_fields()

        candidate_moves_list = []
        if not merge_into:
            self._update_candidate_moves_list(candidate_moves_list)
        else:
            candidate_moves_list.append(merge_into | self)

        # Move removed after merge
        moves_to_unlink = self.env['stock.move']
        # Moves successfully merged
        merged_moves = self.env['stock.move']
        # Emptied moves
        moves_to_cancel = self.env['stock.move']

        moves_by_neg_key = defaultdict(lambda: self.env['stock.move'])
        # Need to check less fields for negative moves as some might not be set.
        neg_qty_moves = self.filtered(
            lambda m: float_compare(m.product_qty, 0.0, precision_rounding=m.product_uom.rounding) < 0)
        # Detach their picking as they will either get absorbed or create a backorder, so no extra logs will be put in the chatter
        neg_qty_moves.picking_id = False
        excluded_fields = self._prepare_merge_negative_moves_excluded_distinct_fields()
        neg_key = itemgetter(*[field for field in distinct_fields if field not in excluded_fields])
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')

        for candidate_moves in candidate_moves_list:
            # First step find move to merge.
            candidate_moves = candidate_moves.filtered(
                lambda m: m.state not in ('done', 'cancel', 'draft')) - neg_qty_moves
            context = self._context
            model = None
            if 'params' in context and 'model' in context['params']:
                model = context['params']['model']
            if self._context.get('button_mark_done_production_ids') or self._context.get('active_model')=='mrp.production' or self._context.get('display_detailed_backorder'):
                for __, g in groupby(candidate_moves, key=itemgetter(*distinct_fields)):
                    moves = self.env['stock.move'].concat(*g)
                    # Merge all positive moves together
                    if len(moves) > 1 and any(m in self for m in moves):
                        # link all move lines to record 0 (the one we will keep).
                        moves.mapped('move_line_ids').write({'move_id': moves[0].id})
                        # merge move data
                        moves[0].write(moves._merge_moves_fields())
                        # update merged moves dicts
                        moves_to_unlink |= moves[1:]
                        merged_moves |= moves[0]
                        moves = moves[0]
                    for m in moves:
                        moves_by_neg_key[neg_key(m)] |= m
            else:
                for __, g in groupby(candidate_moves, key=itemgetter(*distinct_fields)):
                    moves = self.env['stock.move'].concat(*g)
                    # Merge all positive moves together
                    # if len(moves) > 1:
                    # link all move lines to record 0 (the one we will keep).
                    # moves.mapped('move_line_ids').write({'move_id': moves[0].id})
                    # merge move data
                    # moves[0].write(moves._merge_moves_fields())
                    # update merged moves dicts
                    # moves_to_unlink |= moves[1:]
                    # merged_moves |= moves[0]
                    # Add the now single positive move to its limited key record
                    moves_by_neg_key[neg_key(moves[0])] |= moves[0]

        for neg_move in neg_qty_moves:
            # Check all the candidates that matches the same limited key, and adjust their quantities to absorb negative moves
            for pos_move in moves_by_neg_key.get(neg_key(neg_move), []):
                currency_prec = pos_move.product_id.currency_id.decimal_places
                rounding = min(currency_prec, price_unit_prec)
                if float_compare(pos_move.price_unit, neg_move.price_unit, precision_digits=rounding) == 0:
                    new_total_value = pos_move.product_qty * pos_move.price_unit + neg_move.product_qty * neg_move.price_unit
                    # If quantity can be fully absorbed by a single move, update its quantity and remove the negative move
                    if float_compare(pos_move.product_uom_qty, abs(neg_move.product_uom_qty),
                                     precision_rounding=pos_move.product_uom.rounding) >= 0:
                        pos_move.product_uom_qty += neg_move.product_uom_qty
                        pos_move.write({
                            'price_unit': float_round(new_total_value / pos_move.product_qty,
                                                      precision_digits=price_unit_prec) if pos_move.product_qty else 0,
                            'move_dest_ids': [Command.link(m.id) for m in neg_move.mapped('move_dest_ids') if
                                              m.location_id == pos_move.location_dest_id],
                            'move_orig_ids': [Command.link(m.id) for m in neg_move.mapped('move_orig_ids') if
                                              m.location_dest_id == pos_move.location_id],
                        })
                        merged_moves |= pos_move
                        moves_to_unlink |= neg_move
                        if float_is_zero(pos_move.product_uom_qty, precision_rounding=pos_move.product_uom.rounding):
                            moves_to_cancel |= pos_move
                        break
                    neg_move.product_uom_qty += pos_move.product_uom_qty
                    neg_move.price_unit = float_round(new_total_value / neg_move.product_qty,
                                                      precision_digits=price_unit_prec)
                    pos_move.product_uom_qty = 0
                    moves_to_cancel |= pos_move

        if moves_to_unlink:
            # We are using propagate to False in order to not cancel destination moves merged in moves[0]
            moves_to_unlink._clean_merged()
            moves_to_unlink._action_cancel()
            moves_to_unlink.sudo().unlink()

        if moves_to_cancel:
            moves_to_cancel._action_cancel()

        return (self | merged_moves) - moves_to_unlink

    # def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
    #                               owner_id=None,
    #                               strict=True):
    #     taken_quantity = super(StockMove, self)._update_reserved_quantity(need=need,
    #                                                                       available_quantity=available_quantity,
    #                                                                       location_id=location_id, lot_id=lot_id,
    #                                                                       package_id=package_id, owner_id=owner_id,
    #                                                                       strict=strict)
    #     print("ttttttttttttttttttttttttttt",taken_quantity)
    #     uom_qty = self.product_qty / self.product_uom_qty
    #     return taken_quantity



    #
#     def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
#                                   owner_id=None, strict=True):
#         """ Create or update move lines.
#         """
#         if self.product_id.tracking == 'lot':
#             self.ensure_one()
#
#             if not lot_id:
#                 lot_id = self.env['stock.lot']
#             if not package_id:
#                 package_id = self.env['stock.quant.package']
#             if not owner_id:
#                 owner_id = self.env['res.partner']
#
#             # do full packaging reservation when it's needed
#             if self.product_packaging_id and self.product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
#                 available_quantity = self.product_packaging_id._check_qty(available_quantity, self.product_id.uom_id,
#                                                                           "DOWN")
#
#             taken_quantity = need
#             uom_qty = self.product_qty / self.product_uom_qty
#
#             # `taken_quantity` is in the quants unit of measure. There's a possibility that the move's
#             # unit of measure won't be respected if we blindly reserve this quantity, a common usecase
#             # is if the move's unit of measure's rounding does not allow fractional reservation. We chose
#             # to convert `taken_quantity` to the move's unit of measure with a down rounding method and
#             # then get it back in the quants unit of measure with an half-up rounding_method. This
#             # way, we'll never reserve more than allowed. We do not apply this logic if
#             # `available_quantity` is brought by a chained move line. In this case, `_prepare_move_line_vals`
#             # will take care of changing the UOM to the UOM of the product.
#             if not strict and self.product_id.uom_id != self.product_uom:
#                 taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom,
#                                                                                    rounding_method='DOWN')
#                 taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id,
#                                                                     rounding_method='HALF-UP')
#
#             quants = []
#             rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
#
#             if self.product_id.tracking == 'serial':
#                 if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
#                     taken_quantity = 0
#
#             self.env.flush_all()
#             try:
#                 with self.env.cr.savepoint():
#                     if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
#                         quants = self.env['stock.quant']._update_reserved_lot_quantity(
#                             self.product_id, location_id, taken_quantity, uom_qty, lot_id=lot_id,
#                             package_id=package_id, owner_id=owner_id, strict=strict
#                         )
#             except UserError:
#                 taken_quantity = 0
#
#             # Find a candidate move line to update or create a new one.
#             serial_move_line_vals = []
#             for reserved_quant, quantity in quants:
#                 to_update = next(
#                     (line for line in self.move_line_ids if line._reservation_is_updatable(quantity, reserved_quant)),
#                     False)
#                 if to_update:
#                     uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update.product_uom_id,
#                                                                             rounding_method='HALF-UP')
#                     uom_quantity = float_round(uom_quantity, precision_digits=rounding)
#                     uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(uom_quantity,
#                                                                                                   self.product_id.uom_id,
#                                                                                                   rounding_method='HALF-UP')
#                 if to_update and float_compare(quantity, uom_quantity_back_to_product_uom,
#                                                precision_digits=rounding) == 0:
#                     to_update.with_context(bypass_reservation_update=True).reserved_uom_qty += uom_quantity
#                 else:
#                     if self.product_id.tracking == 'serial':
#                         # Move lines with serial tracked product_id cannot be to-update candidates. Delay the creation to speed up candidates search + create.
#                         serial_move_line_vals.extend(
#                             [self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant) for i in
#                              range(int(quantity))])
#                     else:
#                         self.env['stock.move.line'].create(
#                             self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
#
#             self.env['stock.move.line'].create(serial_move_line_vals)
#             return taken_quantity
#         else:
#             res = super(StockMove, self)._update_reserved_quantity(need, available_quantity, location_id, lot_id=lot_id,
#                                                                     package_id=package_id, owner_id=owner_id, strict=strict)
#             return res
#
#
# class StockMoveLine(models.Model):
#     _inherit = "stock.move.line"
#
#     @api.model
#     def create(self, vals_list):
#         return super(StockMoveLine, self).create(vals_list)
#
#
# class StockQuant(models.Model):
#     _inherit = 'stock.quant'
#
#
#     @api.model
#     def _update_reserved_lot_quantity(self, product_id, location_id, quantity, uom_qty, lot_id=None, package_id=None, owner_id=None, strict=False):
#         """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
#         sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
#         the *exact same characteristics* otherwise. Typically, this method is called when reserving
#         a move or updating a reserved move line. When reserving a chained move, the strict flag
#         should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
#         anything from the stock, so we disable the flag. When editing a move line, we naturally
#         enable the flag, to reflect the reservation according to the edition.
#
#         :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
#             was done and how much the system was able to reserve on it
#         """
#         self = self.sudo()
#         rounding = product_id.uom_id.rounding
#         quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
#         quants = quants.filtered(lambda x: x.lot_id.product_qty == uom_qty)
#         reserved_quants = []
#
#         if float_compare(quantity, 0, precision_rounding=rounding) > 0:
#             # if we want to reserve
#             quant_available = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity'))
#             quant_reserved = sum(quants.mapped('reserved_quantity'))
#             available_quantity = quant_available - quant_reserved
#             if float_compare(uom_qty, available_quantity, precision_rounding=rounding) > 0:
#                 raise UserError(_('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
#         elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
#             # if we want to unreserve
#             available_quantity = sum(quants.mapped('reserved_quantity'))
#             if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
#                 raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
#         else:
#             return reserved_quants
#
#         for quant in quants:
#             if float_compare(quantity, 0, precision_rounding=rounding) > 0:
#                 max_quantity_on_quant = quant.quantity - quant.reserved_quantity
#                 if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
#                     continue
#                 max_quantity_on_quant = min(max_quantity_on_quant, quantity)
#                 quant.reserved_quantity += max_quantity_on_quant
#                 reserved_quants.append((quant, max_quantity_on_quant))
#                 quantity -= max_quantity_on_quant
#                 available_quantity -= max_quantity_on_quant
#             else:
#                 max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
#                 quant.reserved_quantity -= max_quantity_on_quant
#                 reserved_quants.append((quant, -max_quantity_on_quant))
#                 quantity += max_quantity_on_quant
#                 available_quantity += max_quantity_on_quant
#
#             if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
#                 break
#         return reserved_quants
