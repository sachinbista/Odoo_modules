# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.model
    def default_get(self, fields):
        if len(self.env.context.get('active_ids', list())) > 1:
            raise UserError("You may only return one picking at a time!")
        res = super(ReturnPicking, self).default_get(fields)

        move_dest_exists = False
        product_return_moves = []

        picking = self.env['stock.picking'].browse(
            self.env.context.get('active_id'))
        backorder_qty = []
        if picking:
            if picking.stock_transfer_id and picking.picking_type_code in [
                    'incoming', 'outgoing'] and not self._context.get(
                        'action_cancel', False) and not self._context.get(
                            'backorder_id', False):
                raise UserError(_(
                    "This operation is not allowed,"
                    " to return products at this stage"
                    ", please create a new inter-company resupply order."))
            res.update({'picking_id': picking.id})
            if picking.state != 'done':
                raise UserError(_("You may only return Done pickings"))
            if self.env.context.get('backorder_id'):
                backorder_picking_id = self.env['stock.picking'].browse(
                    self.env.context.get('backorder_id'))
                if backorder_picking_id and \
                        backorder_picking_id.state == 'cancel':
                    for move in backorder_picking_id.move_ids:
                        backorder_qty += [(move.product_id.id,
                                           move.product_uom_qty)]

            for move in picking.move_ids:
                if move.state == 'cancel':
                    continue
                if move.scrapped:
                    continue
                if move.move_dest_ids:
                    move_dest_exists = True
                quantity = 0.0
                if backorder_qty:
                    for return_qty in backorder_qty:
                        if move.product_id.id == return_qty[0] and \
                                move.product_qty >= return_qty[1]:
                            quantity = return_qty[1]
                            break
                else:
                    quantity = move.product_qty - sum(
                        move.move_dest_ids.filtered(lambda m: m.state in [
                            'partially_available', 'assigned', 'done']
                        ).mapped('move_line_ids').mapped('reserved_qty'))
                    quantity = float_round(
                        quantity, precision_rounding=move.product_uom.rounding)
                product_return_moves.append((0, 0, {
                    'product_id': move.product_id.id,
                    'quantity': quantity,
                    'move_id': move.id,
                    'uom_id': move.product_id.uom_id.id
                }))

            if not product_return_moves:
                raise UserError(_("No products to return (only lines in Done "
                                  "state and not fully returned yet can be "
                                  "returned)!"))
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': product_return_moves})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': move_dest_exists})
            if 'parent_location_id' in fields and \
                    picking.location_id.usage == 'internal':
                res.update({
                    'parent_location_id': picking.picking_type_id.warehouse_id
                    and picking.picking_type_id.warehouse_id.view_location_id.id or
                    picking.location_id.location_id.id
                })
            if 'original_location_id' in fields:
                res.update({'original_location_id': picking.location_id.id})
            if 'location_id' in fields:
                location_id = picking.location_id.id
                if picking.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                    location_id = picking.picking_type_id.return_picking_type_id.default_location_dest_id.id
                res['location_id'] = location_id
        return res

    def _create_returns(self):
        ctx = dict(self._context)
        if ctx.get('active_id', False):
            picking = self.env['stock.picking'].browse(
                ctx['active_id'])
            if picking.stock_transfer_id:
                if picking.stock_transfer_id.transfer_type == 'inter_company':
                    ctx.update(
                        {'intercomp_call_to_change_bypass_method': True})
                new_picking_id, pick_type_id = super(
                    ReturnPicking, self.with_context(ctx))._create_returns()
                new_picking_id = self.env['stock.picking'].browse(
                    new_picking_id)
                new_picking_id.write({
                    'stock_transfer_id': picking.stock_transfer_id.id,
                    'return_picking': True,
                })
                if not new_picking_id.prev_picking_id:
                    new_picking_id.prev_picking_id = picking.id
                return new_picking_id.id, pick_type_id
            else:
                return super(ReturnPicking, self)._create_returns()
        else:
            return super(ReturnPicking, self)._create_returns()
