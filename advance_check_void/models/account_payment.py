# -*- coding: utf-8 -*-

from odoo import api, fields, models, Command, _
from datetime import datetime
from datetime import date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(selection_add=[
        ('void', 'Void')
    ], ondelete={'void': 'cascade'})


class AccountPayment(models.Model):
    _name = "account.payment"
    _inherit = ['account.payment', 'mail.thread', 'mail.activity.mixin',
                'portal.mixin']
    _order = 'create_date desc'

    # state = fields.Selection(selection_add=[('void', 'Void')])
    is_void = fields.Boolean('Is Void?')
    is_hide_check = fields.Boolean('Hide Check Number?')
    is_visible_check = fields.Boolean(
        'Is Visible Check',
        help='Use for the visible or invisible check number.')
    is_readonly_check = fields.Boolean(
        'Is Readonly Check',
        help='Use for the readonly or editable check number.')

    @api.onchange('payment_method_id')
    def onchange_payment_method(self):
        '''Allow to customer payment to enter check number.
           - Based on journal check printing manual True/False for vendor.'''
        self.is_visible_check = False
        self.is_readonly_check = False
        if self.payment_method_id:
            if self.payment_method_id.payment_type == 'inbound' and \
            self.payment_method_code == 'check_printing':
                self.is_visible_check = True
                self.check_number = 0
            elif self._context.get('is_vendor'):
                if self.payment_method_id.payment_type == 'outbound' and \
                self.payment_method_code == 'check_printing':
                    self.is_visible_check = False
            elif self.payment_method_id.payment_type == 'outbound' and \
            self.payment_method_code == 'check_printing':
                self.is_visible_check = True
                if not self.check_manual_sequencing:
                    self.is_readonly_check = True

    def print_checks(self):
        for rec in self:
            if rec.payment_type == 'outbound':
                is_manual = rec.journal_id.check_manual_sequencing
                if not rec.check_number and is_manual:
                    rec.check_number = rec.journal_id.check_next_number
                    rec.is_hide_check = False
                    rec.journal_id.write({
                        'check_next_number': rec.journal_id.check_next_number + 1})
                    message = ('''<ul class="o_mail_thread_message_tracking">
                                    <li>Check Updated Date: %s</li>
                                    <li>Check Number: %s (Generated)</li>
                                    <li>State: %s</li>
                                  </ul>''') % (
                                      datetime.now().strftime(
                                          DEFAULT_SERVER_DATE_FORMAT),
                                      rec.check_number, rec.state.title())
                    rec.message_post(body=message)
        result = super(AccountPayment, self).print_checks()
        return result

    def unmark_as_sent(self):
        '''Void Check.................'''
        result = super(AccountPayment, self).unmark_as_sent()
        payment_check_void_obj = self.env['payment.check.void']
        check_hist_obj = self.env['payment.check.history']
        for rec in self:
            c_date = str(rec.create_date)
            split_string = c_date.split(".", 1)
            substring = split_string[0]
            create_date_res = datetime.strptime(
                substring, DEFAULT_SERVER_DATETIME_FORMAT).strftime(
                    DEFAULT_SERVER_DATE_FORMAT)
            payment_check_void_obj.create({
                'bill_ref': rec.name,
                'create_date': create_date_res,
                'check_number': rec.check_number,
                'state': 'void',
                'payment_id': rec.id})
            rec.write({'is_hide_check': True})
            # Update payment check history..
            check_ids = check_hist_obj.search([
                ('payment_id', '=', rec.id),
                ('check_number', '=', rec.check_number)],
                order='id desc', limit=1)
            if check_ids:
                check_ids.write({'state': 'posted'})
        return result

    def action_draft(self):
        result = super(AccountPayment, self).action_draft()
        for rec in self:
            rec.is_void = False

    def action_unmark_sent(self):
        '''Void Check.................'''
        if self.reconciled_statement_lines_count > 0:
            raise ValidationError(_("First you should unlink this payment from the statement."))
        result = super(AccountPayment, self).action_unmark_sent()
        payment_check_void_obj = self.env['payment.check.void']
        check_hist_obj = self.env['payment.check.history']
        for rec in self:
            c_date = str(rec.create_date)
            split_string = c_date.split(".", 1)
            substring = split_string[0]
            create_date_res = datetime.strptime(
                substring, DEFAULT_SERVER_DATETIME_FORMAT).strftime(
                    DEFAULT_SERVER_DATE_FORMAT)
            today_date = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
            message = ('''<table border="1" style="text-align: center; width:600px;">
                            <tr>
                                <td>Bill Number</td>
                                <td>Void Check Number</td>
                                <td>Check Voided Date</td>
                                <td>Status</td>
                            </tr>
                            <tr>
                                <td>%s</td>
                                <td>%s</td>
                                <td>%s</td>
                                <td>%s</td>
                            </tr>
                          </table>
                        ''') % (rec.ref or '', rec.check_number or '',
                                today_date or '', rec.state.title() or '')
            rec.message_post(body=message)
            payment_check_void_obj.create({
                'bill_ref': rec.name,
                'create_date': create_date_res,
                'check_number': rec.check_number,
                'state': 'void',
                'payment_id': rec.id})
            rec.write({'is_hide_check': True, 'is_void': False,
                       'is_move_sent': False})
            # Update payment check history..
            check_ids = check_hist_obj.search([
                ('payment_id', '=', rec.id),
                ('check_number', '=', rec.check_number)], order='id desc',
                limit=1)
            if check_ids:
                check_ids.write({'state': 'posted'})
        return result

    @api.model
    def create(self, vals):
        if vals.get('check_number') and not str(vals.get('check_number')
                                                ).isdigit():
            raise ValidationError(_('Check number must be integer.'))
        vals.update({'check_number': vals.get('check_number')})
        res = super(AccountPayment, self).create(vals)

        # If paymen method is check.
        if vals.get('check_manual_sequencing') and vals.get('check_number'):
            res.write({'is_hide_check': False})
            message = ('''<ul class="o_mail_thread_message_tracking">
                            <li>Check Updated Date: %s</li>
                            <li>Check Number: %s (Generated)</li>
                            <li>State: %s</li>
                          </ul>
                        ''') % (datetime.now().strftime(
                            DEFAULT_SERVER_DATE_FORMAT),
                            res.check_number, res.state.title())
            res.message_post(body=message)

        check_hist_obj = self.env['payment.check.history']
        if res:
            self._cr.execute(
                "update account_payment set create_uid='" + str(
                    self._uid) + "' where id='" + str(res.id) + "'")
        if 'check_number' in vals and vals['check_number'] and res.check_number:
            check_hist = {'name': res.name,
                          'payment_id': res.id,
                          'partner_id': res.partner_id.id,
                          'amount': res.amount,
                          # 'amount': res.amount + res.payment_term_discount,
                          'check_number': res.check_number,
                          'check_amount': res.amount,
                          # 'discount': res.payment_term_discount,
                          'journal_id': res.journal_id.id,
                          'date': fields.Date.context_today(res),
                          'create_date': fields.Date.context_today(res),
                          'write_date': fields.Date.context_today(res),
                          'create_uid': res.create_uid.id,
                          'state': res.state,
                          'is_visible_check': True if res.check_number else False,
                          }
            check_hist_obj.create(check_hist)
        return res

    def write(self, vals):
        # check_number = self.check_number
        if vals.get('check_number') and not str(vals.get(
            'check_number')).isdigit():
            raise ValidationError(_('Check number must be integer.'))
        result = super(AccountPayment, self).write(vals)
        check_hist_obj = self.env['payment.check.history']
        for res in self:
            new_chk_id = False
            self._cr.execute(
                "update account_payment set write_uid='" + str(
                    self._uid) + "' where id='" + str(res.id) + "'")
            if 'check_number' in vals and vals['check_number'] and res.check_number:
                check_hist = {
                    'name': res.name,
                    'payment_id': res.id,
                    'partner_id': res.partner_id.id,
                    'amount': res.amount,
                    # 'amount': res.amount + res.payment_term_discount,
                    'check_amount': res.amount,
                    'check_number': res.check_number,
                    # 'discount': res.payment_term_discount,
                    'journal_id': res.journal_id.id,
                    'date': fields.Date.context_today(res),
                    'create_date': fields.Date.context_today(res),
                    'write_date': fields.Date.context_today(res),
                    'create_uid': res.create_uid.id,
                    'state': res.state,
                    'is_visible_check': True if res.check_number else False,
                    }
                new_chk_id = check_hist_obj.create(check_hist)
            if new_chk_id:
                check_ids = check_hist_obj.search([
                    ('payment_id', '=', res.id),
                    ('check_number', '=', res.check_number),
                    ('id', '!=', new_chk_id.id)], order='id DESC', limit=1)
            else:
                check_ids = check_hist_obj.search([
                    ('payment_id', '=', res.id),
                    ('write_date', '<=', res.write_date)], order='id desc',
                    limit=1)
            if check_ids:
                for chk in check_ids:
                    if res.state == 'sent':
                        continue
                    chk.write({'state': res.state})
        return result

    def cancel(self):
        if self.check_number and self.payment_type == 'outbound':
            raise ValidationError(_('''
            You can not allow cancelling payment because a check is already printed.'''))
        result = super(AccountPayment, self).cancel()
        payment_check_history_obj = self.env['payment.check.history']
        domain = [('payment_id', '=', self.id),
                  ('partner_id', '=', self.partner_id.id),
                  ('journal_id', '=', self.journal_id.id)]
        if self.check_number:
            domain += [('check_number', '=', self.check_number)]
        payment_check_history_ids = payment_check_history_obj.search(
            domain, order='id DESC', limit=1)
        payment_check_history_ids.write({'state': 'cancel'})

        # Set Messages....
        message = ('''<ul class="o_mail_thread_message_tracking">
                        <li>Updated On: %s</li>
                        <li>Check Number: %s (Cancel)</li>
                        <li>State: %s</li>
                      </ul>
                    ''') % (datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
                            self.check_number, self.state.title())
        self.message_post(body=message)
        self.write({'is_hide_check': True})
        return result

    def void_check_reversal_payment(self):
        if self.reconciled_statement_lines_count > 0:
            raise ValidationError(_("First you should unlink this payment from the statement."))
        journal_id = self.journal_id and self.journal_id.id
        self._cr.execute('''
        SELECT DISTINCT(ap.move_id) FROM account_payment AS ap
        INNER JOIN account_move_line AS aml
        ON aml.payment_id=ap.id
            AND ap.id = %s
        INNER JOIN account_move AS am
            ON aml.move_id = am.id''' % (self.id))
        am_ids = self._cr.fetchone()

        if am_ids:
            am_ids = am_ids[0]
        # self.action_unmark_sent()
        return {
                'name': _('Reverse Moves'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move.reversal',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'is_void_button': True,
                    'default_journal_id': journal_id or False,
                }
        }

    def open_reverse_move(self):
        self.ensure_one()
        return {
            'name': _("Reverse Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.move_id.reversed_entry_id.id,
        }

    def button_void_checks(self):
        return {
            'name': _('Void Checks'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'payment.check.void',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('payment_id', 'in', self.ids)],
        }

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for record in self:
            if record.payment_type == 'inbound' and record.\
                payment_method_code == 'check_printing' and \
                not record.move_id and not record.check_number:
                 raise ValidationError(_("Please Enter Check Number"))
        return res


class PaymentCheckHistory(models.Model):
    _name = "payment.check.history"
    _description = "Payment Info for the check Payment Feature"
    _order = "write_date desc"

    name = fields.Char('Name', readonly=True)
    payment_id = fields.Many2one(
        'account.payment', string="Payment Info", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner", readonly=True)
    amount = fields.Float('Gross Amount', readonly=True)
    check_number = fields.Integer('Check Number', readonly=True)
    check_amount = fields.Float('Check Amount', readonly=True)
    # discount = fields.Float('Discount Amount', readonly=True)
    journal_id = fields.Many2one('account.journal', 'Journal', readonly=True)
    date = fields.Date(string="Date", readonly=True)
    create_date = fields.Datetime(string="Create Date", readonly=True)
    write_date = fields.Datetime(string="Write Date", readonly=True)
    create_uid = fields.Many2one(
        comodel_name='res.users', string="Created By", readonly=True)
    write_uid = fields.Many2one(
        comodel_name='res.users', string="Updated By", readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('posted', 'Posted'), ('sent', 'Sent'),
         ('void', 'Void'), ('cancel', 'Cancel'), ('reconciled', 'Reconciled')],
        readonly=True, default='draft', copy=False, string="Status",
        track_visibility='onchange')
    currency_id = fields.Many2one(
        related="payment_id.currency_id", string="Currency",
        readonly=True, store=True)
    is_visible_check = fields.Boolean('Is Visible Check')


class PaymentCheckVoid(models.Model):
    _name = "payment.check.void"
    _description = "Payment Check Void"
    _order = 'check_number'

    bill_ref = fields.Char('Bill Number')
    create_date = fields.Date('Check Void Date')
    check_number = fields.Integer('Check Number')
    state = fields.Selection([('void', 'Void')], string='State', default='void')
    payment_id = fields.Many2one('account.payment', 'Payment')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _description = "Journal Item"

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * exchange_partials:    A recorset of all account.partial.reconcile created during the reconciliation
                                        with the exchange difference journal entries.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {'exchange_partials': self.env['account.partial.reconcile']}

        if not self:
            return results

        not_paid_invoices = self.move_id.filtered(lambda move:
            move.is_invoice(include_receipts=True)
            and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if not self._context.get('is_void_button') and not self._context.get('is_payment_import'):
                if line.reconciled:
                    raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.account_type not in ('asset_cash', 'liability_credit_card'):
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        if self._context.get('reduced_line_sorting'):
            sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id)
        else:
            sorting_f = lambda line: (line.date_maturity or line.date, line.currency_id, line.amount_currency)
        sorted_lines = self.sorted(key=sorting_f)

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines._all_reconciled_lines()
        involved_partials = involved_lines.matched_credit_ids | involved_lines.matched_debit_ids

        # ==== Create partials ====

        partial_no_exch_diff = bool(self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))
        sorted_lines_ctx = sorted_lines.with_context(no_exchange_difference=self._context.get('no_exchange_difference') or partial_no_exch_diff)
        partials = sorted_lines_ctx._create_reconciliation_partials()
        results['partials'] = partials
        involved_partials += partials
        exchange_move_lines = partials.exchange_move_id.line_ids.filtered(lambda line: line.account_id == account)
        involved_lines += exchange_move_lines
        exchange_diff_partials = exchange_move_lines.matched_debit_ids + exchange_move_lines.matched_credit_ids
        involved_partials += exchange_diff_partials
        results['exchange_partials'] += exchange_diff_partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.account_type in ('asset_receivable', 'liability_payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        def is_line_reconciled(line, has_multiple_currencies):
            # Check if the journal item passed as parameter is now fully reconciled.
            return line.reconciled \
                   or (line.company_currency_id.is_zero(line.amount_residual)
                       if has_multiple_currencies
                       else line.currency_id.is_zero(line.amount_residual_currency)
                   )

        has_multiple_currencies = len(involved_lines.currency_id) > 1
        if all(is_line_reconciled(line, has_multiple_currencies) for line in involved_lines):
            # ==== Create the exchange difference move ====
            # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
            # when importing a full accounting including the reconciliation like Winbooks.

            exchange_move = self.env['account.move']
            caba_lines_to_reconcile = None
            if not self._context.get('no_exchange_difference'):
                # In normal cases, the exchange differences are already generated by the partial at this point meaning
                # there is no journal item left with a zero amount residual in one currency but not in the other.
                # However, after a migration coming from an older version with an older partial reconciliation or due to
                # some rounding issues (when dealing with different decimal places for example), we could need an extra
                # exchange difference journal entry to handle them.
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                exchange_max_date = date.min
                for line in involved_lines:
                    if not line.company_currency_id.is_zero(line.amount_residual):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual': line.amount_residual})
                    elif not line.currency_id.is_zero(line.amount_residual_currency):
                        exchange_lines_to_fix += line
                        amounts_list.append({'amount_residual_currency': line.amount_residual_currency})
                    exchange_max_date = max(exchange_max_date, line.date)
                exchange_diff_vals = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    company=involved_lines[0].company_id,
                    exchange_date=exchange_max_date,
                )

                # Exchange difference for cash basis entries.
                # If we are fully reversing the entry, no need to fix anything since the journal entry
                # is exactly the mirror of the source journal entry.
                if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
                    caba_lines_to_reconcile = involved_lines._add_exchange_difference_cash_basis_vals(exchange_diff_vals)

                # Create the exchange difference.
                if exchange_diff_vals['move_vals']['line_ids']:
                    exchange_move = involved_lines._create_exchange_difference_move(exchange_diff_vals)
                    if exchange_move:
                        exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                        # Track newly created lines.
                        involved_lines += exchange_move_lines

                        # Track newly created partials.
                        exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                                 + exchange_move_lines.matched_credit_ids
                        involved_partials += exchange_diff_partials
                        results['exchange_partials'] += exchange_diff_partials

            # ==== Create the full reconcile ====
            results['full_reconcile'] = self.env['account.full.reconcile'] \
                .with_context(
                    skip_invoice_sync=True,
                    skip_invoice_line_sync=True,
                    skip_account_move_synchronization=True,
                    check_move_validity=False,
                ) \
                .create({
                    'exchange_move_id': exchange_move and exchange_move.id,
                    'partial_reconcile_ids': [Command.set(involved_partials.ids)],
                    'reconciled_line_ids': [Command.set(involved_lines.ids)],
                })

            # === Cash basis rounding autoreconciliation ===
            # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
            # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)

            if caba_lines_to_reconcile:
                for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                    if not account.reconcile:
                        continue

                    exchange_line = exchange_move.line_ids.filtered(
                        lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                    )

                    (exchange_line + amls_to_reconcile).filtered(lambda l: not l.reconciled).reconcile()

        not_paid_invoices.filtered(lambda move:
            move.payment_state in ('paid', 'in_payment')
        )._invoice_paid_hook()

        return results


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    check_number = fields.Char('Check Number')

    def _create_payment_vals_from_wizard(self, batch_result):
        res = super()._create_payment_vals_from_wizard(batch_result)
        if self.payment_type == 'inbound' and \
            self.payment_method_code == 'check_printing' and \
            not self.check_number:
            raise ValidationError(_("Please Enter Check Number"))

        if self.payment_type == 'inbound' and \
            self.payment_method_code == 'check_printing':
            res.update({
                'check_number': self.check_number,
                'is_visible_check': True if self.check_number else False
                })
        if self.payment_type == 'outbound' and \
            self.payment_method_code == 'check_printing':
            res.update({
                'is_visible_check': True
                })
        return res
