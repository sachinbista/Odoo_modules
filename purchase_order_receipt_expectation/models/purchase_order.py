# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    receipt_expectation = fields.Selection([('automatic', 'Automatic'), ('manual', 'Manual')],
                              string='Receipt Expectation', default='manual', required=True)
    is_manually_shipped = fields.Boolean(compute="_compute_is_manully_shipped")

    @api.constrains('order_line')
    def check_manual_quantity(self):
        for line in self.order_line:
            if line.manually_received_qty_uom != 0.0 and line.product_qty < line.manually_received_qty_uom:
                # line.product_qty = line.manually_received_qty_uom
                raise UserError(_("After manual receiving, quantity should not be decreased!"))

    def button_open_manual_receipt_wizard(self):
        """ Open the Manual Receipt wizard to create pickings for the selected lines.
                :return: An action opening the purchase.order.manual.receipt.wizard . """
        return {
            'name': _('Create Manual Receipt'),
            'res_model': 'purchase.order.manual.receipt.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'purchase.order',
                'active_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _create_picking(self):
        if self.receipt_expectation == 'manual':
            return
        else:
            super(PurchaseOrder, self)._create_picking()

    @api.depends('order_line')
    def _compute_is_manully_shipped(self):
        for order in self:
            if order.order_line and any(x.manually_received_qty_uom < x.product_qty for x in order.order_line):
                order.is_manually_shipped = False 
            else:
                order.is_manually_shipped = True