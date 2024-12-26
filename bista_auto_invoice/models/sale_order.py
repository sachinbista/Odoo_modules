# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoices_to_post = fields.Many2many('account.move',
                                        relation="sale_order_invoice_to_post_ids",
                                        column1="sale_order_id",
                                        column2="invoice_id")

    def _generate_invoice(self, picking):
        invoiceable = False
        for order in self:
            if not order.payment_term_id.auto_invoice:
                self -= order
            if not invoiceable:
                invoiceable = any(line.qty_to_invoice for line in order.order_line)
        
        if not self or not invoiceable:
            return

        payment = self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': self.ids,
        }).create({
            'advance_payment_method': 'delivered',
        })
        payment.create_invoices()
        invoice_ids = self.mapped('invoices_to_post')
        invoice_ids.action_post()
        return invoice_ids


    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super(SaleOrder, self)._create_invoices(grouped, final, date)
        self.write({'invoices_to_post': [(6, 0, moves.ids)]})
        return moves
