
import json

from odoo import fields, models, api,_
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
# Since invoice amounts are unsigned, this is how we know if money comes in
# or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}


#inherit account.move class and add new two state ('send_approval'
#and 'payment_to_pay') in state field (only vendor bills)
class AccountMove(models.Model):
    _inherit = "account.move"

    approval_status = fields.Selection([('send_approval', 'Send for Approval'),
                                        ('cancel_approval', 'Cancel Approval'),
                                        ('payment_to_pay', 'Approved to Pay'),
                                        ('cancel_approval_to_pay', 'Cancel Approved to Pay')
                                        ],string="Approval Status", tracking=True, copy=False)

    def _compute_payments_widget_to_reconcile_info(self):
        result = super(AccountMove,self)._compute_payments_widget_to_reconcile_info()
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            if move.move_type != 'in_refund':
                domain = [
                    ('account_id', 'in', pay_term_lines.account_id.ids),
                    ('parent_state', '=', 'posted'),
                    ('partner_id', '=', move.commercial_partner_id.id),
                    ('reconciled', '=', False),
                    '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                ]

            if move.move_type == 'in_refund':
                domain = [
                    ('account_id', 'in', pay_term_lines.account_id.ids),
                    ('parent_state', '=', 'posted'),
                    ('move_id.approval_status', '=', 'payment_to_pay'),
                    ('partner_id', '=', move.commercial_partner_id.id),
                    ('reconciled', '=', False),
                    '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency_id': move.currency_id.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True
        return result

    # def _write(self, vals):
    #     pre_not_reconciled = self.filtered(lambda invoice: not invoice.reconciled)
    #     pre_reconciled = self - pre_not_reconciled
    #     res = super(AccountMove, self)._write(vals)
    #     reconciled = self.filtered(lambda invoice: invoice.reconciled)
    #     not_reconciled = self - reconciled
    #     (reconciled & pre_reconciled).filtered(lambda invoice: invoice.state == 'payment_to_pay').action_invoice_paid()
    #     (not_reconciled & pre_not_reconciled).filtered(lambda invoice: invoice.state == 'paid').action_invoice_re_open()
    #     return res

    # def action_invoice_paid(self):
    #     # lots of duplicate calls to action_invoice_paid, so we remove those already paid
    #     to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
    #     for rec in self:
    #         if rec.type in ('in_invoice','in_refund'):
    #             if to_pay_invoices.filtered(lambda inv: inv.state not in  ('open','payment_to_pay')):# and (inv.type not in 'in_invoice','in_refund')):
    #                 raise UserError(_('Invoice must be validated in order to set it to register payment.'))
    #         else:
    #             if to_pay_invoices.filtered(lambda inv: inv.state != 'open'):# and inv.type not in ('out_invoice','out_refund')):
    #                 raise UserError(_('Invoice must be validated in order to set it to register payment.'))
    #     if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
    #         raise UserError(_('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))
    #     return to_pay_invoices.write({'state': 'paid'})

    #state move to Send for Approval
    def send_for_approval(self):
        if self.move_type == 'in_invoice' and self.state == 'posted' and self.payment_state == 'not_paid':
            self.write({'approval_status': 'send_approval'})

    #state move to Approved to Pay
    def payment_to_pay(self):
        if self.move_type == 'in_invoice' and self.approval_status in 'send_approval':
            self.write({'approval_status': 'payment_to_pay'})

    #State move back to Open from Approved To Pay
    def cancel_payment_to_pay(self):
        if self.env.user.has_group('account.group_account_manager') and \
            self.move_type == 'in_invoice' and \
            self.approval_status in 'payment_to_pay':
            self.write({'approval_status': 'cancel_approval_to_pay'})

    def cancel_send_for_approval(self):
        if self.move_type == 'in_invoice' and self.approval_status in 'send_approval':
            self.write({'approval_status': 'cancel_approval'})

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        if self.approval_status and self.move_type == 'in_invoice':
            self.write({'approval_status': False})
        return False



    def action_register_payment(self):
        res = super(AccountMove, self).action_register_payment()
        for move in self:
            if move.approval_status != 'payment_to_pay' and move.move_type in ('in_invoice', 'in_receipt'):
                raise UserError(_("You can not register payment before approval."))
        return res

    # def _get_outstanding_info_JSON(self):
    #     """
    #     Method overridden and overwritten as well.
    #     Overridden method will be called if its not supplier invoice.
    #     Else Overwritten method will be called.
    #     Purpose : To make visible Add button and Outstanding Message appeared
    #     Top of the invoices visible only in approved to pay state.
    #     """
    #     if self.type not in ('in_invoice', 'in_refund'):
    #         super(AccountMove, self)._get_outstanding_info_JSON()
    #     if self.type in ('in_invoice', 'in_refund'):
    #         self.outstanding_credits_debits_widget = json.dumps(False)
    #         if self.state == 'payment_to_pay':
    #             domain = [('account_id', '=', self.account_id.id), ('partner_id', '=', self.env['res.partner']._find_accounting_partner(self.partner_id).id), ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0)]
    #             if self.type in ('out_invoice', 'in_refund'):
    #                 domain.extend([('credit', '>', 0), ('debit', '=', 0)])
    #                 type_payment = _('Outstanding credits')
    #             else:
    #                 domain.extend([('credit', '=', 0), ('debit', '>', 0)])
    #                 type_payment = _('Outstanding debits')
    #             info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': self.id}
    #             lines = self.env['account.move.line'].search(domain)
    #             currency_id = self.currency_id
    #             if len(lines) != 0:
    #                 for line in lines:
    #                     # get the outstanding residual value in invoice currency
    #                     if line.currency_id and line.currency_id == self.currency_id:
    #                         amount_to_show = abs(line.amount_residual_currency)
    #                     else:
    #                         amount_to_show = line.company_id.currency_id.with_context(date=line.date).compute(abs(line.amount_residual), self.currency_id)
    #                     if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
    #                         continue
    #                     info['content'].append({
    #                         'journal_name': line.ref or line.move_id.name,
    #                         'amount': amount_to_show,
    #                         'currency': currency_id.symbol,
    #                         'id': line.id,
    #                         'position': currency_id.position,
    #                         'digits': [69, self.currency_id.decimal_places],
    #                     })
    #                 info['title'] = type_payment
    #                 self.outstanding_credits_debits_widget = json.dumps(info)
    #                 self.has_outstanding = True


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    batch_boolean = fields.Boolean(string="Batch")

    def get_payments_vals(self):
        '''Overwrite a default function
        '''
        if self.multi:
            groups = self._groupby_invoices()
            return [self._prepare_payment_vals(invoices) for invoices in groups.values()]

        # Following if condition added
        # Bug #2320 - Vendor & Customer Invoices register Payment not
        # working correctly while doing from Tree view(do it one or
        # multiple)
        if not self.invoice_ids and self._context.get('active_ids', ''):
            self.invoice_ids = self._context.get('active_ids', '')
        return [self._prepare_payment_vals(self.invoice_ids)]

    # def action_create_payments(self):
    #     move_ids = self.env['account.move'].browse(self._context.get('active_ids'))
    #     for move_id in move_ids:
    #         # Check all invoices write in posted state for supplier
    #         if move_id.state == 'payment_to_pay' and move_id.move_type in ('in_invoice', 'in_refund'):
    #             move_id.write({'state': 'posted'})
    #     return super(AccountPaymentRegister, self).action_create_payments()

    # @api.model
    # def default_get(self, fields_list):
    #     '''
    #             default_get(fields) -> default_values
    #
    #             Return default values for the fields in ``fields_list``. Default
    #             values are determined by the context, user defaults, and the model
    #             itself.
    #
    #             :param fields_list: a list of field names
    #             :return: a dictionary mapping each field name to its corresponding
    #                 default value, if it has one.
    #
    #             This method is overwritten(calling directly ORM method to eliminate validation for multiple vendor)
    #             '''
    #     res = models.Model.default_get(self, fields_list=fields_list)
    #
    #     if 'line_ids' in fields_list and 'line_ids' not in res:
    #
    #         # Retrieve moves to pay from the context.
    #
    #         if self._context.get('active_model') == 'account.move':
    #             lines = self.env['account.move'].browse(self._context.get('active_ids', [])).line_ids
    #         elif self._context.get('active_model') == 'account.move.line':
    #             lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
    #         else:
    #             raise UserError(_(
    #                 "The register payment wizard should only be called on account.move or account.move.line records."
    #             ))
    #
    #         if 'journal_id' in res and not self.env['account.journal'].browse(res['journal_id']) \
    #                 .filtered_domain([('company_id', '=', lines.company_id.id), ('type', 'in', ('bank', 'cash'))]):
    #             # default can be inherited from the list view, should be computed instead
    #             del res['journal_id']
    #
    #         # Keep lines having a residual amount to pay.
    #         available_lines = self.env['account.move.line']
    #         for line in lines:
    #             # Check all invoices are open (Customer)
    #             if line.move_id.state != 'posted' and line.move_id.move_type in ('out_invoice', 'out_refund'):
    #                 raise UserError(_("You can only register payment for posted journal entries."))
    #
    #                 # Check all invoices are open (supplier)
    #                 if (line.move_id.state != 'payment_to_pay' and line.move_id.move_type in ('in_invoice', 'in_refund') and line.move_id.payment_state == 'not_paid') or (line.move_id.state != 'posted' and line.move_id.move_type in ('in_invoice', 'in_refund') and line.move_id.payment_state == 'partial'):
    #                     raise UserError(_("You can only register payments for Approved to pay invoices."))
    #
    #             if line.account_type not in ('asset_receivable', 'liability_payable'):
    #                 continue
    #             if line.currency_id:
    #                 if line.currency_id.is_zero(line.amount_residual_currency):
    #                     continue
    #             else:
    #                 if line.company_currency_id.is_zero(line.amount_residual):
    #                     continue
    #             available_lines |= line
    #
    #         # Check.
    #         if not available_lines:
    #             raise UserError(
    #                 _("You can't register a payment because there is nothing left to pay on the selected journal items."))
    #         if len(lines.company_id) > 1:
    #             raise UserError(_("You can't create payments for entries belonging to different companies."))
    #         if len(set(available_lines.mapped('account_type'))) > 1:
    #             raise UserError(
    #                 _("You can't register payments for journal items being either all inbound, either all outbound."))
    #
    #         res['line_ids'] = [(6, 0, available_lines.ids)]
    #
    #     return res
