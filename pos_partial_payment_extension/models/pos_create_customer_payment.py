# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


class pos_create_customer_payment(models.Model):
    _inherit = 'pos.create.customer.payment'
    _description = "POS Create Customer Payment"


    def create_customer_payment_inv(self, partner_id, journal, amount, invoice, note):
        if 'pos_create_payment' in self._context:
            pos_payment_object = self.env['pos.payment']
            partner_object = self.env['res.partner']
            partner_id =  partner_object.browse(partner_id)
            inv_obj = self.env['account.move'].search([('id', '=', invoice['id'])], limit=1)
            pos_order = inv_obj.pos_order_id

            vals = {
                'payment_method_id': int(journal),
                'currency_id': inv_obj.currency_id.id,
                'currency': inv_obj.currency_id.name,
                'pos_reference': note,
                'payment_date': fields.Date.today(),
                'pos_order_id': pos_order.id,
                'session_id': pos_order.session_id.id,
                'amount': amount
            }
            pos_payment_id = pos_payment_object.create(vals)
            payment_moves = pos_payment_id._create_payment_moves()
            receivable_account = self.env["res.partner"]._find_accounting_partner(partner_id).with_company(
                self.env.company).property_account_receivable_id
            if receivable_account.reconcile:
                invoice_receivables = inv_obj.pos_order_id.account_move.line_ids.filtered(
                    lambda line: line.account_id == receivable_account and not line.reconciled)
                if invoice_receivables:
                    payment_receivables = payment_moves.mapped('line_ids').filtered(
                        lambda line: line.account_id == receivable_account and line.partner_id)
                    (invoice_receivables | payment_receivables).sudo().with_company(self.env.company).reconcile()
            return True
        return super().create_customer_payment_inv(partner_id, journal, amount, invoice, note)
