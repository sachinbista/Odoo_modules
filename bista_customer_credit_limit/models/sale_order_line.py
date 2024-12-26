# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import AccessDenied


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    partner_id = fields.Many2one('res.partner', related="order_id.partner_id", store=True)

    def _get_to_invoice_value(self):

        line = self
        if line.product_uom_qty == line.qty_invoiced:
            return 0
        paid_value = 0
        if line.qty_invoiced:

            move_line_env = self.env['account.move.line']
            unpaid_invoice = move_line_env.search([('move_id.state', '!=', 'posted'),
                                                   ('sale_line_ids', '=', line.id )])

            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            paid_value = price * line.qty_invoiced if not unpaid_invoice else 0
        return line.price_subtotal - paid_value

