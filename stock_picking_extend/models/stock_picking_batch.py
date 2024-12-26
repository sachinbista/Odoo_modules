# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date

class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    landed_cost_status = fields.Selection([('pending', 'Pending'),('done', 'Done'), ('cancel', 'Not Required')], default='pending', string="Landed Cost Status")

    @api.depends('name','state','picking_ids')
    def _compute_remaining_days(self):
        for batch in self:
            if batch.date_eta and batch.landed_cost_status == 'pending':
                batch.remaining_days = (batch.date_eta - date.today()).days
            else:
                batch.remaining_days = 0
                
    remaining_days = fields.Integer(string='Remaining Days', compute='_compute_remaining_days')

    @api.depends('name','state', 'picking_ids', 'picking_ids.state','picking_ids.move_ids')
    def _compute_purchase_order_bool(self):
        for batch in self:
            batch.purchase_order_bool = False
            if batch.picking_ids:
                for picking_id in batch.picking_ids:
                    if picking_id.container_id == batch.name:
                        if picking_id.move_ids.mapped('purchase_line_id'):
                            batch.purchase_order_bool = True

    purchase_order_bool = fields.Boolean(string='Check link with PO', store=True, compute='_compute_purchase_order_bool')

    def action_done(self):
        pickings = self.mapped('picking_ids').filtered(lambda picking: picking.state not in ('cancel', 'done'))
        pickings.with_context(from_batchtransfer=True).button_validate()
        return super().action_done()

    def action_cancel(self):
        self.landed_cost_status = 'cancel'
        return super().action_cancel()

    def button_update_landed_cost(self):
        batch_ids = self.search([('state', '=', 'cancel')])
        for batch_id in batch_ids:
            batch_id.landed_cost_status = 'cancel'


    def action_put_in_pack(self):
        """ Action to put move lines with 'Done' quantities into a new pack
        This method follows same logic to stock.picking.
        """
        self.ensure_one()
        if self.state not in ('done', 'cancel'):
            move_lines_by_picking = {}
            for move_line in self.move_line_ids.filtered(lambda x: x.qty_done > 0 and not x.result_package_id.id):
                current_picking_id = move_line.picking_id.id
                if (
                    current_picking_id not in move_lines_by_picking
                    and move_line.qty_done > 0
                ):
                    move_lines_by_picking[current_picking_id] = [move_line]
                elif move_line.qty_done > 0:
                    move_lines_by_picking[current_picking_id].append(move_line)

            move_line_ids = self.picking_ids[0]._package_move_lines()
            res = self.env['stock.quant.package']
            if move_line_ids:
                for picking_id, move_lines in move_lines_by_picking.items():
                    move_line_ids = [move_line.id for move_line in move_lines]
                    move_lines_recordset = self.env['stock.move.line'].browse(move_line_ids)
                    res= move_lines[0].picking_id._put_in_pack(move_lines_recordset, False)
                return res
            else:
                raise UserError(_("Please add 'Done' quantities to the batch picking to create a new pack."))