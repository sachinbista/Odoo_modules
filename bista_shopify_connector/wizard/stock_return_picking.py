# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.exceptions import UserError
from odoo import _, api, fields, models


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        move_dest_exists = False
        product_return_moves = [(5,)]
        if self.picking_id and self.picking_id.state != 'done':
            raise UserError(_("You may only return Done pickings."))
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [
            f for f in self.env['stock.return.picking.line']._fields.keys()]
        product_return_moves_data_tmpl = self.env['stock.return.picking.line'].default_get(
            line_fields)
        serial_tracking = set(self.picking_id.move_ids.mapped(
            'product_id').mapped('tracking'))
        usages = [move.location_dest_id.usage for move in self.picking_id.move_ids]
        sale = self.picking_id.group_id.sale_id
        if 'customer' in usages and sale and sale.id:
            if len(serial_tracking) == 1:
                for movel in self.picking_id.move_line_ids:
                    if movel.state == 'cancel':
                        continue
                    product_return_moves_data = {
                        'product_id': movel.product_id.id,
                        'quantity': movel.quantity,
                        'move_id': movel.move_id.id,
                        'uom_id': movel.product_id.uom_id.id,
                        'lot_id': movel.lot_id and movel.lot_id.id or False,
                    }
                    product_return_moves.append(
                        (0, 0, product_return_moves_data))
        else:
            for move in self.picking_id.move_ids:
                if move.state == 'cancel':
                    continue
                if move.scrapped:
                    continue
                if move.move_dest_ids:
                    move_dest_exists = True
                product_return_moves_data = dict(
                    product_return_moves_data_tmpl)
                product_return_moves_data.update(
                    self._prepare_stock_return_picking_line_vals_from_move(move))
                product_return_moves.append((0, 0, product_return_moves_data))
        if self.picking_id and not product_return_moves:
            raise UserError(
                _("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.picking_id:
            self.product_return_moves = product_return_moves
            self.move_dest_exists = move_dest_exists
            self.parent_location_id = self.picking_id.picking_type_id.warehouse_id and self.picking_id.picking_type_id.warehouse_id.view_location_id.id or self.picking_id.location_id.location_id.id
            self.original_location_id = self.picking_id.location_id.id
            location_id = self.picking_id.location_id.id
            if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = location_id

    def _create_returns(self):
        usages = [move.location_dest_id.usage for move in self.picking_id.move_ids]
        sale_id = self.picking_id.group_id.sale_id
        # for return_line in self.product_return_moves:
        #     if 'customer' in usages and sale_id:
                # if not return_line.return_line_reason:
                #     raise UserError(
                #         _("Please add return reason for respective IMEI number."))
                # if return_line.lot_id:
                #     return_line.lot_id.write(
                #         {'lot_issue': return_line.return_line_reason})
        res = super(ReturnPicking, self)._create_returns()
        return res


class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")
    return_line_reason = fields.Char(string="Return Reason")


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_outgoing_incoming_moves(self):
        outgoing_moves = self.env['stock.move']
        incoming_moves = self.env['stock.move']

        moves = self.move_ids.filtered(
            lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id)
        if self._context.get('accrual_entry_date'):
            moves = moves.filtered(lambda r: fields.Date.context_today(
                r, r.date) <= self._context['accrual_entry_date'])
        for move in moves:
            if move.to_refund is False:
                move.update({'to_refund': True})
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    outgoing_moves |= move
            elif move.location_dest_id.usage != "customer" and move.to_refund and not move.picking_id.claim_id:
                incoming_moves |= move
        return outgoing_moves, incoming_moves
