# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.exceptions import UserError


class SaleOrderPayment(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _get_default_journal(self):
        return self.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash')),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    quick_pay = fields.Boolean(help="If True, this will auto register payment for the generated invoice")
    payment_method_id = fields.Many2one('account.payment.method.line')
    journal_id = fields.Many2one('account.journal', default=_get_default_journal)
    available_payment_method_ids = fields.One2many(related="journal_id.inbound_payment_method_line_ids")
    company_id = fields.Many2one('res.company', default=lambda x: x.env.company.id)


    def create_invoices(self):
        ret = super(SaleOrderPayment, self).create_invoices()
        if self.quick_pay:
            sale_order_ids = self.sale_order_ids

            if len(sale_order_ids) > 1:
                raise UserError("You cannot use quick pay for multiple sales orders")
            if not self.payment_method_id:
                raise UserError("Select a payment method and try again.")
            if not self.journal_id:
                raise UserError("Select a journal and try again.")

            order = sale_order_ids[0]
            invoice_ids = order.invoice_ids.sorted(lambda x: x.id, reverse=True)
            if not invoice_ids:
                raise UserError("Invoice not found. please contact system administrator")

            invoice = invoice_ids[0]
            invoice.action_post()
            inv_payment_wizard = self.env['account.payment.register']
            inv_payment_wizard.with_context(active_model='account.move',
                                            active_ids=[invoice.id]).create(
                {'payment_method_line_id': self.payment_method_id.id,
                 'journal_id': self.journal_id.id,
                 'amount': invoice.amount_total})._create_payments()
        return ret
