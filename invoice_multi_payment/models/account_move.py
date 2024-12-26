# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"

    related_payment_id = fields.Many2one('account.payment',
                                            string="Related Payment",
                                            copy=False)
    remittance_discount = fields.Float('Remittance Discount')

    def js_assign_outstanding_line(self, line_id):
        res = super(AccountMove, self).js_assign_outstanding_line(
            line_id=line_id)
        lines = self.env['account.move.line'].browse(line_id)
        if len(lines) == 1 and lines.move_id.payment_id:
            lines.move_id.payment_id.created_from_register_payment = True
        return res

    def button_draft(self):
        """remove all outstanding utilization when move related to current payment is cancelled"""
        res = super(AccountMove, self).button_draft()
        for rec in self:
            if rec.payment_id:
                partial_ids = self.env['account.partial.reconcile'].search(
                    [('payment_id', '=', rec.payment_id.id)])
                partial_ids.unlink()
                rec.payment_id.created_from_register_payment = False
                rec.payment_id.invoice_lines.write({'state': 'draft'})
            if rec.related_payment_id and not self._context.get('allow_draft'):
                raise UserError("You can not cancel carry forward payment entry.")
        return res

    def _compute_payments_widget_reconciled_info(self):
        result = super(AccountMove,self)._compute_payments_widget_reconciled_info()
        for move in self:
            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                payment_lst = []
                reconciled_val = []
                if move.invoice_payments_widget:
                    for inv_pay_widget in move.invoice_payments_widget['content']:
                        if inv_pay_widget['account_payment_id'] not in payment_lst:
                            payment_id = self.env['account.payment'].browse(inv_pay_widget['account_payment_id'])
                            if payment_id.invoice_lines:
                                payment_lst.append(inv_pay_widget['account_payment_id'])
                                reconciled_val.append(inv_pay_widget)
                            else:
                                reconciled_val.append(inv_pay_widget)
                    for r in range(len(reconciled_val)):
                        amount = 0.0
                        for i in range(len(move.invoice_payments_widget['content'])):
                            if reconciled_val[r]['account_payment_id'] == move.invoice_payments_widget['content'][i]['account_payment_id']:
                                payment_id = self.env['account.payment'].browse(move.invoice_payments_widget['content'][i]['account_payment_id'])
                                if payment_id.invoice_lines:
                                    amount += move.invoice_payments_widget['content'][i]['amount']
                        if amount != 0.0:
                            reconciled_val[r]['amount'] = amount
                    move.invoice_payments_widget['content'] = reconciled_val
        return result

    @api.depends('amount_residual', 'move_type', 'state', 'company_id')
    def _compute_payment_state(self):
        res = super(AccountMove, self)._compute_payment_state()

        payment_id = False
        for invoice in self:
            if invoice.related_payment_id:
                payment_id = invoice.related_payment_id
                break

        # filtered_invoice = []
        if payment_id:
            payment_id._compute_outstanding_amount()
            # filtered_invoice = [line.invoice_id.id for line in payment_id.invoice_lines]

        # invoice_amount = 0
        # paid_amount = 0
        # payment_state = False
        # for invoice in self:
        #     if invoice.payment_state == 'invoicing_legacy':
        #         # invoicing_legacy state is set via SQL when setting setting field
        #         # invoicing_switch_threshold (defined in account_accountant).
        #         # The only way of going out of this state is through this setting,
        #         # so we don't recompute it here.
        #         continue
        #
        #     payment_state_matters = invoice.is_invoice(True)
        #     if payment_state_matters and invoice.payment_state in ('in_payment','paid'):
        #         # invoice_amount = invoice.amount_total
        #         if payment_id and invoice.id not in filtered_invoice:
        #                 payment_state = invoice.payment_state
        #                 invoice_amount += invoice.amount_total
        #
        #
        #     if invoice.related_payment_id:
        #         # payment_id = invoice.related_payment_id
        #         paid_amount = invoice.amount_total
        #
        # if payment_id:
        #     payment_id.write({'carry_forward_paid':invoice_amount})
        #     payment_id._get_remaining_amount()
        #     payment_id._compute_outstanding_amount()

        # if payment_id and payment_state != 'not_paid':
        #     if invoice_amount < paid_amount:
        #         payment_id.write({'carry_forward_paid': payment_id.carry_forward_paid + invoice_amount})
        #     else:
        #         payment_id.write({'carry_forward_paid': payment_id.carry_forward_paid + paid_amount})
        #     payment_id._get_remaining_amount()
        # elif payment_id:
        #     payment_id.write({'carry_forward_paid': 0})
        #     payment_id._get_remaining_amount()
        return res

class AccountMoveLines(models.Model):
    _inherit = "account.move.line"

    is_discount = fields.Boolean(string="Is Discount", copy=False,
                                 default=False)
    is_sale_tax = fields.Boolean(string="Sales Tax", copy=False, default=False)
    is_writeoff = fields.Boolean(string="Write-Off", copy=False, default=False)
    is_extra_line = fields.Boolean(string="Extra Line", copy=False,
                                   default=False, help="Flag for writeoff AR/AP line")
    is_carry_forward = fields.Boolean(string="Carry Forward", copy=False,
                                      default=False)

    @api.model
    def _prepare_reconciliation_partials(self, vals_list):
        ''' override this method to add custom payment allocation logic
        '''
        if not self._context.get('allocation_line_vals'):
            return super(AccountMoveLines,
                         self)._prepare_reconciliation_partials(vals_list)

        def fix_remaining_cent(currency, abs_residual, partial_amount):
            if abs_residual - currency.rounding <= partial_amount <= abs_residual + currency.rounding:
                return abs_residual
            else:
                return partial_amount

        """here we removed current payment ml id from self and add it at the end of self,
        otherwise its utilising payment first based on maturity date"""
        outstanding_payment_ids = self._context.get('outstanding_payment_ids')
        if outstanding_payment_ids:
            self -= outstanding_payment_ids
            self += outstanding_payment_ids
        current_payment_id = self._context.get('current_payment_id')
        payment_id = self._context.get('payment_id')

        # here we need to utilize outstanding first and current payment at last, so we swap current payment
        # at last position
        if current_payment_id in self:
            self -= current_payment_id
            self += current_payment_id

        debit_lines = iter(self.filtered(
            lambda line: line.balance > 0.0 or line.amount_currency > 0.0))
        credit_lines = iter(self.filtered(
            lambda line: line.balance < 0.0 or line.amount_currency < 0.0))
        debit_line = None
        credit_line = None

        debit_amount_residual = 0.0
        debit_amount_residual_currency = 0.0
        credit_amount_residual = 0.0
        credit_amount_residual_currency = 0.0
        debit_line_currency = None
        credit_line_currency = None

        partials_vals_list = []
        exchange_data = {}
        allocation_line_vals = self._context.get('allocation_line_vals', {})
        while True:

            # Move to the next available debit line.
            if not debit_line:
                debit_line = next(debit_lines, None)
                if not debit_line:
                    break

                amount_allocation = allocation_line_vals.get(debit_line.id)
                if amount_allocation:
                    debit_amount_residual = amount_allocation
                else:
                    debit_amount_residual = debit_line.amount_residual

                if debit_line.currency_id:
                    if amount_allocation:
                        debit_amount_residual_currency = amount_allocation
                    else:
                        debit_amount_residual_currency = debit_line.amount_residual_currency
                    debit_line_currency = debit_line.currency_id
                else:
                    debit_amount_residual_currency = debit_amount_residual
                    debit_line_currency = debit_line.company_currency_id

            # Move to the next available credit line.
            if not credit_line:
                credit_line = next(credit_lines, None)
                if not credit_line:
                    break
                amount_allocation = allocation_line_vals.get(credit_line.id)
                credit_amount_residual = amount_allocation if amount_allocation else credit_line.amount_residual

                if credit_line.currency_id:
                    if amount_allocation:
                        credit_amount_residual_currency = amount_allocation
                    else:
                        credit_amount_residual_currency = credit_line.amount_residual_currency
                    credit_line_currency = credit_line.currency_id
                else:
                    credit_amount_residual_currency = credit_amount_residual
                    credit_line_currency = credit_line.company_currency_id

            min_amount_residual = min(debit_amount_residual,
                                      -credit_amount_residual)
            has_debit_residual_left = not debit_line.company_currency_id.is_zero(
                debit_amount_residual) and debit_amount_residual > 0.0
            has_credit_residual_left = not credit_line.company_currency_id.is_zero(
                credit_amount_residual) and credit_amount_residual < 0.0
            has_debit_residual_curr_left = not debit_line_currency.is_zero(
                debit_amount_residual_currency) and debit_amount_residual_currency > 0.0
            has_credit_residual_curr_left = not credit_line_currency.is_zero(
                credit_amount_residual_currency) and credit_amount_residual_currency < 0.0

            if debit_line_currency == credit_line_currency:
                # Reconcile on the same currency.

                # The debit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the credit_line is not an exchange difference one.
                if not has_debit_residual_curr_left and (
                        has_credit_residual_curr_left or not has_debit_residual_left):
                    debit_line = None
                    continue

                # The credit line is now fully reconciled because:
                # - either amount_residual & amount_residual_currency are at 0.
                # - either the debit is not an exchange difference one.
                if not has_credit_residual_curr_left and (
                        has_debit_residual_curr_left or not has_credit_residual_left):
                    credit_line = None
                    continue

                min_amount_residual_currency = min(
                    debit_amount_residual_currency,
                    -credit_amount_residual_currency)
                min_debit_amount_residual_currency = min_amount_residual_currency
                min_credit_amount_residual_currency = min_amount_residual_currency

            else:
                # Reconcile on the company's currency.

                # The debit line is now fully reconciled since amount_residual
                # is 0.
                if not has_debit_residual_left:
                    debit_line = None
                    continue

                # The credit line is now fully reconciled since amount_residual
                # is 0.
                if not has_credit_residual_left:
                    credit_line = None
                    continue

                min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                    min_amount_residual, debit_line.currency_id, credit_line.company_id, credit_line.date, )
                min_debit_amount_residual_currency = fix_remaining_cent(
                    debit_line.currency_id,
                    debit_amount_residual_currency,
                    min_debit_amount_residual_currency,
                )
                min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                    min_amount_residual, credit_line.currency_id, debit_line.company_id, debit_line.date, )
                min_credit_amount_residual_currency = fix_remaining_cent(
                    credit_line.currency_id,
                    -credit_amount_residual_currency,
                    min_credit_amount_residual_currency,
                )

            debit_amount_residual -= min_amount_residual
            debit_amount_residual_currency -= min_debit_amount_residual_currency
            credit_amount_residual += min_amount_residual
            credit_amount_residual_currency += min_credit_amount_residual_currency
            if debit_line in outstanding_payment_ids:
                if debit_line.payment_id:
                    debit_line.payment_id.created_from_register_payment = True
                    credit_line.payment_id._compute_check_all_posted()
            if credit_line in outstanding_payment_ids:
                if credit_line.payment_id:
                    credit_line.payment_id.created_from_register_payment = True
                    credit_line.payment_id._compute_check_all_posted()
            partials_vals_list.append({
                'amount': min_amount_residual,
                'debit_amount_currency': min_debit_amount_residual_currency,
                'credit_amount_currency': min_credit_amount_residual_currency,
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
                'payment_id': payment_id if payment_id else False,
            })

        return partials_vals_list, exchange_data
