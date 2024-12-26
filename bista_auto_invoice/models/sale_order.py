# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoices_to_post = fields.Many2many('account.move',
                                        relation="sale_order_invoice_to_post_ids",
                                        column1="sale_order_id",
                                        column2="invoice_id")

    payment_term_ribbon = fields.Boolean(
        string="Payment Term Ribbon",
        compute="_compute_payment_term_ribbon",
        store=True
    )
    ribbon_text = fields.Char(
        string="Ribbon Text",
        compute="_compute_payment_term_ribbon",
        store=True
    )

    @api.depends('payment_term_id')
    def _compute_payment_term_ribbon(self):
        for order in self:
            payment_term = order.payment_term_id
            if payment_term and payment_term.payment_term_ribbon:
                order.payment_term_ribbon = True
                order.ribbon_text = "Payment Term: " + payment_term.name
            else:
                order.payment_term_ribbon = False
                order.ribbon_text = ''

    def _generate_invoice(self, picking=None):
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
        # payment.create_invoices()
        payment.with_context(autosend_email=True).create_invoices()
        invoice_ids = self.mapped('invoices_to_post')
        invoice_ids.sudo().action_post()
        invoice_ids.want_to_send_email = True
        return invoice_ids


    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super(SaleOrder, self)._create_invoices(grouped, final, date)
        self.write({'invoices_to_post': [(6, 0, moves.ids)]})
        return moves
