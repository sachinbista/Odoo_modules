from lxml import etree

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_multi_deduction = fields.Boolean()
    linked_bill_ids = fields.Many2many('account.move', 'rel_bill_payment', 'invoice_id', 'payment_id',
                                       string='Linked Bills', copy=False, readonly=False)
    reconciled_linked_bill_ids = fields.Many2many('account.move', 'rel_reconciled_linked_bill_payment', 'payment_id',
                                                  'invoice_id',
                                                  compute='_compute_reconciled_linked_bill_invoice_ids',
                                                  string='Reconciled Linked Bills', store=True, copy=False)
    reconciled_linked_invoice_ids = fields.Many2many('account.move', 'rel_reconciled_linked_invoice_payment',
                                                     'payment_id', 'invoice_id',
                                                     compute='_compute_reconciled_linked_bill_invoice_ids',
                                                     string='Reconciled Linked Invoices', store=True, copy=False)

    active = fields.Boolean('Active', tracking=True, default=True)

    @api.depends('linked_bill_ids', 'state', 'linked_bill_ids.state', 'linked_bill_ids.amount_residual', 'linked_bill_ids.payment_state')
    def _compute_reconciled_linked_bill_invoice_ids(self):
        stored_payments = self.filtered('id')
        for pay in stored_payments:
            if self._context.get('unreconciled_move_ids'):
                move_ids = self._context.get('unreconciled_move_ids')
            else:
                move_ids = pay.linked_bill_ids
            reconciled_linked_invoice_ids = reconciled_linked_bill_ids = self.env['account.move']
            payment_model = pay._fields.keys()
            has_invoice_lines = False
            if 'invoice_lines' in payment_model:
                has_invoice_lines = True
            if move_ids:
                if move_ids[0].move_type in self.env['account.move'].get_sale_types(True):
                    for invoice in move_ids:
                        # check if invoice is paid or not with this payment
                        invoice_ml_ids = pay.linked_bill_ids.mapped('line_ids').filtered(
                            lambda x: x.account_id.account_type in ('asset_receivable', 'liability_payable'))
                        for partial, amount, counterpart_line in invoice._get_reconciled_invoices_partials()[0]:
                            if counterpart_line and counterpart_line.payment_id and counterpart_line.payment_id.id == pay.id:
                                pass
                            elif partial.debit_move_id.id in invoice_ml_ids.ids and partial.credit_move_id.id in invoice_ml_ids.ids:
                                reconciled_linked_invoice_ids |= invoice
                    if self._context.get('unreconciled_move_ids'):
                        move_to_unlink_ids = move_ids.filtered(lambda x: x.id not in reconciled_linked_invoice_ids.ids)
                        for move_to_unlink in move_to_unlink_ids:
                            pay.reconciled_linked_invoice_ids = [(3, move_to_unlink.id)]
                            pay.linked_bill_ids = [(3, move_to_unlink.id)]
                    elif has_invoice_lines and pay.invoice_lines:
                        partial_ids = self.env['account.partial.reconcile'].search(
                            [('payment_id', '=', pay.id)])
                        move_ids = partial_ids.mapped('debit_move_id').mapped(
                            'move_id') + partial_ids.mapped('credit_move_id').mapped(
                            'move_id')
                        move_ids = self.env['account.move'].search(
                            [('id', 'in', move_ids.ids), ('move_type', '!=', 'entry')])
                        pay.reconciled_linked_invoice_ids = [(6, 0, move_ids.ids)]
                        pay.linked_bill_ids = [(6, 0, move_ids.ids)]
                    else:
                        pay.reconciled_linked_invoice_ids = [(6, 0, reconciled_linked_invoice_ids.ids)]
                        pay.linked_bill_ids = [(6, 0, reconciled_linked_invoice_ids.ids)]

                else:
                    bill_ml_ids = pay.linked_bill_ids.mapped('line_ids').filtered(
                        lambda x: x.account_id.account_type in ('asset_receivable', 'liability_payable'))
                    for bill in move_ids:
                        for partial, amount, counterpart_line in bill._get_reconciled_invoices_partials()[0]:
                            if counterpart_line.payment_id and counterpart_line.payment_id.id == pay.id:
                                pass
                            elif partial.debit_move_id.id in bill_ml_ids.ids and partial.credit_move_id.id in bill_ml_ids.ids:
                                reconciled_linked_bill_ids |= bill
                    if self._context.get('unreconciled_move_ids'):
                        move_to_unlink_ids = move_ids.filtered(lambda x: x.id not in reconciled_linked_bill_ids.ids)
                        for move_to_unlink in move_to_unlink_ids:
                            pay.reconciled_linked_bill_ids = [(3, move_to_unlink.id)]
                            pay.linked_bill_ids = [(3, move_to_unlink.id)]
                    elif has_invoice_lines and pay.invoice_lines:
                        partial_ids = self.env['account.partial.reconcile'].search(
                            [('payment_id', '=', pay.id)])
                        move_ids = partial_ids.mapped('debit_move_id').mapped(
                            'move_id') + partial_ids.mapped('credit_move_id').mapped(
                            'move_id')
                        move_ids = self.env['account.move'].search(
                            [('id', 'in', move_ids.ids), ('move_type', '!=', 'entry')])
                        pay.reconciled_linked_bill_ids = [(6, 0, move_ids.ids)]
                        pay.linked_bill_ids = [(6, 0, move_ids.ids)]
                    else:
                        pay.reconciled_linked_bill_ids = [(6, 0, reconciled_linked_bill_ids.ids)]
                        pay.linked_bill_ids = [(6, 0, reconciled_linked_bill_ids.ids)]

    def action_draft(self):
        """override to unreconciled bills/refund which is reconciled with each other and linked with same payment group"""
        # reconciled_statement_ids  = self.sudo().reconciled_statement_ids
        # if reconciled_statement_ids:
        #     raise ValidationError(_("You can not perform this operation because this payment linked with Bank Statement."))
        # batch_payment_id = self.sudo().batch_payment_id
        # if batch_payment_id and batch_payment_id.state == 'reconciled':
        #     raise ValidationError(_("You can not perform this operation because Batch is already reconciled."))
        partial_ids = self.env['account.partial.reconcile']
        if self.reconciled_invoice_ids:
            invoice_ml_ids = self.reconciled_invoice_ids.mapped('line_ids').filtered(lambda x: x.account_id.account_type in ('asset_receivable', 'liability_payable'))
            for invoice in self.reconciled_invoice_ids:
                for partial, amount, counterpart_line in invoice._get_reconciled_invoices_partials()[0]:
                    if counterpart_line.payment_id:
                        pass
                    elif partial.debit_move_id.id in invoice_ml_ids.ids and partial.credit_move_id.id in invoice_ml_ids.ids:
                        partial_ids += partial
        if self.reconciled_bill_ids:
            bill_ml_ids = self.reconciled_bill_ids.mapped('line_ids').filtered(lambda x: x.account_id.account_type in ('asset_receivable', 'liability_payable'))
            for bill in self.reconciled_bill_ids:
                for partial, amount, counterpart_line in bill._get_reconciled_invoices_partials()[0]:
                    if counterpart_line.payment_id:
                        pass
                    elif partial.debit_move_id.id in bill_ml_ids.ids and partial.credit_move_id.id in bill_ml_ids.ids:
                        partial_ids += partial
        partial_ids.unlink()
        self.linked_bill_ids = [(6,0, [])]
        self.reconciled_linked_bill_ids = [(6,0, [])]
        self.reconciled_linked_invoice_ids = [(6,0, [])]
        if not self.active:
            self.active = True

        return super(AccountPayment, self).action_draft()

    # @api.depends('move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    # def _compute_stat_buttons_from_reconciliation(self):
    #     ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
    #     res = super(AccountPayment, self)._compute_stat_buttons_from_reconciliation()
    #     reverse_entry_ids = []
    #     for invoice_id in self.reconciled_invoice_ids:
    #         if invoice_id.move_type == 'out_refund':
    #             if invoice_id.reversed_entry_id.payment_state in ['paid','partial']:
    #                 self.reconciled_invoice_ids += invoice_id.reversed_entry_id
    #         elif invoice_id.move_type == 'out_invoice':
    #                 reverse_entry_ids.append(invoice_id.id)
    #     self.reconciled_invoice_ids += self.env['account.move'].search([('reversed_entry_id', 'in', reverse_entry_ids),('payment_state','in',['paid','partial'])])
    #     self.reconciled_invoices_count = len(self.reconciled_invoice_ids)
    #     return res

    @api.depends('move_id.line_ids.matched_debit_ids', 'move_id.line_ids.matched_credit_ids')
    def _compute_stat_buttons_from_reconciliation(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        res = super(AccountPayment, self)._compute_stat_buttons_from_reconciliation()
        stored_payments = self.filtered('id')
        for pay in stored_payments:
            if pay.linked_bill_ids and pay.linked_bill_ids[0].move_type in self.env['account.move'].get_sale_types(
                    True):
                pay.reconciled_invoice_ids += pay.reconciled_linked_invoice_ids
                pay.reconciled_invoices_count = len(pay.reconciled_invoice_ids)
            elif pay.linked_bill_ids and pay.linked_bill_ids[0].move_type in self.env[
                'account.move'].get_purchase_types(True):
                pay.reconciled_bill_ids += pay.reconciled_linked_bill_ids
                pay.reconciled_bills_count = len(pay.reconciled_bill_ids)
        return res

    def _get_check_key_list(self):
        return ["name", "account_id"]

    def _get_update_key_list(self):
        return ["account_id"]

    def _update_vals_writeoff(
            self, write_off_line_vals, line_vals_list, check_keys, update_keys
    ):
        for line_vals in line_vals_list:
            if all(
                    line_vals[check_key] == write_off_line_vals[check_key]
                    for check_key in check_keys
            ):
                for update_key in update_keys:
                    line_vals[update_key] = write_off_line_vals[update_key]
                break

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Split amount to multi payment deduction
        Concept:
        * Process by payment difference 'Mark as fully paid' and keep value is paid
        * Process by each deduction and keep value is deduction
        * Combine all process and return list
        """
        self.ensure_one()
        check_keys = self._get_check_key_list()
        update_keys = self._get_update_key_list()
        # payment difference
        if isinstance(write_off_line_vals, dict) and write_off_line_vals:
            line_vals_list = super()._prepare_move_line_default_vals(
                write_off_line_vals
            )
            # add analytic on line_vals_list
            self._update_vals_writeoff(
                write_off_line_vals, line_vals_list, check_keys, update_keys
            )
            return line_vals_list
        # multi deduction writeoff
        if isinstance(write_off_line_vals, list) and write_off_line_vals:
            origin_writeoff_amount = [write_off['amount_currency'] for write_off in write_off_line_vals]
            origin_writeoff_amount = sum(origin_writeoff_amount)
            amount_total = sum(writeoff["amount_currency"] for writeoff in write_off_line_vals)
            # write_off_line_vals[0]["amount_currency"] = amount_total
            # write_off_line_vals[0]["balance"] = amount_total
            # cast it to 'Mark as fully paid'
            write_off_reconcile = write_off_line_vals
            line_vals_list = super()._prepare_move_line_default_vals(
                write_off_reconcile
            )
            # line_vals_list.pop(-1)
            # rollback to origin
            # write_off_line_vals[0]["amount_currency"] = origin_writeoff_amount
            multi_deduct_list = [
                super(AccountPayment, self)._prepare_move_line_default_vals(
                    [writeoff_line]
                )[-1]
                for writeoff_line in write_off_line_vals
            ]
            i = 0
            for deduct_list in multi_deduct_list:
                if deduct_list['name'] == 'Discount':
                    multi_deduct_list[i]['is_discount'] = True
                i += 1

            # line_vals_list.extend(multi_deduct_list)
            # add analytic on line_vals_list
            for writeoff_line in write_off_line_vals:
                self._update_vals_writeoff(
                    writeoff_line, line_vals_list, check_keys, update_keys
                )
        else:
            line_vals_list = super()._prepare_move_line_default_vals(
                write_off_line_vals
            )
        return line_vals_list

    def _synchronize_from_moves(self, changed_fields):
        ctx = self._context.copy()
        if all(rec.is_multi_deduction for rec in self):
            ctx["skip_account_move_synchronization"] = True
        return super(
            AccountPayment,
            self.with_context(**ctx),
        )._synchronize_from_moves(changed_fields)

    def _get_writeoff_discount_amount(self):
        self.ensure_one()
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = pay._seek_for_lines()
            writeoff_amount = sum(writeoff_lines.mapped('balance'))
            discount_amount = sum(discount_lines.mapped('balance'))
        return [writeoff_amount,discount_amount]

    @api.model
    def _get_early_payment_discount_balance(self):
        self.ensure_one()
        discount_amount = 0.0
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = pay._seek_for_lines()
            # Search for account.move.line records with label 'Early Payment Discount Amount'
            for writeoff_line in writeoff_lines:
                if writeoff_line.name == 'Early Payment Discount':
                    # Calculate the total balance of the matched lines
                    discount_amount += writeoff_line.balance
        return round(discount_amount, 2)

    @api.model
    def _get_writeoff_balance(self):
        self.ensure_one()
        writeoff_amount = 0.0
        for pay in self:
            liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = pay._seek_for_lines()
            # Search for account.move.line records with label 'writeoff Amount'
            for writeoff_line in writeoff_lines:
                if writeoff_line.name != 'Early Payment Discount':
                    # Calculate the total balance of the matched lines
                    writeoff_amount += writeoff_line.balance
        return round(writeoff_amount, 2)

    def _get_paid_amount(self):
        is_net = self._context.get('is_net')
        self.ensure_one()
        total = 0.0
        if not self.invoice_lines:
            for partial, amount, counterpart_line in self.move_id._get_reconciled_invoices_partials():
                total += amount
            if not is_net:
                total -= self._get_writeoff_amount()

            return abs(total)
        else:
            partial_ids = self.env['account.partial.reconcile'].search([('payment_id', '=', self.id)])
            total = sum(partial_ids.mapped('amount'))
            for partial, amount, counterpart_line in self.move_id._get_reconciled_invoices_partials()[1]:
                if partial.payment_id:
                    continue
                total += amount
            if not is_net:
                total -= (self.writeoff_amount + self.discount_amount)

            return total

        