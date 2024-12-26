# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class AccountAgedReceivable(models.TransientModel):
    _inherit = 'account.receivable.report.wizard'
    _description = 'Account Receivable Details Report'

    report_id = fields.Selection([
        ('aged_recivable','Aged Receivable Report'),
        ('aged_recivable_rollup','Aged Receivable Rollover')
        ], default="aged_recivable")
    date_to = fields.Date(string='To', default=lambda *a: time.strftime('%Y-%m-%d'))
    @api.onchange('date_selection_option')
    def onchange_date_selection_option(self):
        if self.report_id =='aged_recivable_rollup':
            if self.date_selection_option == 'end_of_last_month':
                today = date.today()
                first = today.replace(day=1)
                last_month_end = first - timedelta(days=1)
                last_month_start = last_month_end.replace(day=1)
                self.date_from = last_month_start
                self.date_to = last_month_end
            if self.date_selection_option == 'end_of_last_quarter':
                first_month_of_quarter = ((datetime.now().month - 1) // 3) * 3 + 1
                last_quarter_end = datetime.now().date().replace(
                    month=first_month_of_quarter, day=1) - relativedelta(days=1)
                last_quarter_start = last_quarter_end.replace(month=last_quarter_end.month - 2, day=1)
                self.date_from = last_quarter_start
                self.date_to = last_quarter_end
            if self.date_selection_option == 'end_of_last_fin_year':
                today = date.today()
                last_year = today.year - 1
                self.date_from = today.replace(month=1, day=1, year=last_year)
                self.date_to = today.replace(month=12, day=31, year=last_year)
            if self.date_selection_option == 'custom':
                self.date_from = date.today()
                self.date_to = date.today()
        else:
            return super(AccountAgedReceivable, self).onchange_date_selection_option()

    def create_update_customer_aging(self):
        if self.report_id == "aged_recivable":
            return super(AccountAgedReceivable,self).create_update_customer_aging()
        else:
            company_id = self.env.company.id
            end_date = self.date_to
            start_date = self.date_from
            journal_ids = self.env['account.journal'].sudo().with_context(active_test=False).search([
                    ('company_id', '=',company_id)
                ], order="company_id, name").ids
            if not end_date and not start_date:
                raise ValidationError(_("Please select date to generate the report."))
            uid = self.env.user.id
            self._cr.execute("delete from aged_receivable_rollup where create_uid=%s", [uid])
            if end_date and start_date:
                aging_query = """
                    INSERT INTO aged_receivable_rollup (
                 create_date, 
                 create_uid, 
                 write_date,
                 write_uid, 
                 account_move_id,
                 account_move_line_id,
                 company_id, 
                 account_id,
                 journal_id, 
                 partner_id, 
                 transaction_type,
                 initial_balance, 
                 debit, 
                 credit, 
                 final_balance
                 )                 
                SELECT
                 now(), 
                 %(uid)s, 
                 now(), 
                 %(uid)s,
                 account_move_id, account_move_line_id,
                 company_id, account_id,
                 journal_id, partner_id, transaction_type,
                 sum(initial_balance) AS initial_balance, sum(debit) AS debit, sum(credit) AS credit, 
                 sum(final_balance) as final_balance
                 FROM (
                 SELECT
                    coalesce(aml.id) AS account_move_line_id,
                    coalesce(aml_res.id) AS partner_id,
                    coalesce(am.id) AS account_move_id,
                    coalesce(journal.id) AS journal_id,
                    coalesce(acc.id) AS account_id,
                    sum(
                        aml.balance - COALESCE(
                        (
                            SELECT
                            SUM(amount)
                            FROM account_partial_reconcile
                            WHERE
                            debit_move_id = aml.id
                            AND max_date < %(start_date)s
                        ),0) 
                        + 
                        COALESCE(
                        (SELECT
                         SUM(amount)
                         FROM account_partial_reconcile
                         WHERE credit_move_id = aml.id
                         AND max_date < %(start_date)s ), 0 )) AS initial_balance,
                    0.0 as debit,
                    0.0 as credit,
                    0.0 as final_balance,
                    am.company_id AS company_id,
                    CASE 
                    WHEN am.move_type = 'out_invoice' THEN 'sale'
                    when am.move_type = 'out_refund' THEN 'credit_memo'
                    when am.move_type = 'entry' AND journal.type = 'bank' THEN 'payment_receipt'
                    when am.move_type = 'entry' AND journal.type = 'general' AND journal.code ilike 'STJ' THEN 'adjustments'
                    ELSE 'misc'
                  END AS transaction_type
                    FROM account_move_line aml
                    LEFT JOIN account_move am ON aml.move_id = am.id
                    LEFT JOIN account_payment ap ON aml.payment_id = ap.id
                    LEFT JOIN res_partner aml_res ON aml.partner_id = aml_res.id
                    LEFT JOIN account_account acc ON aml.account_id = acc.id
                    LEFT JOIN account_payment_term apt ON am.invoice_payment_term_id = apt.id
                    LEFT JOIN account_journal journal  ON journal.id = am.journal_id
                    WHERE
                    acc.account_type IN ('asset_receivable') AND aml.partner_id IS NOT null
                    AND aml.balance <> 0 AND am.state = 'posted'
                    AND aml.date < %(start_date)s
                    AND aml.company_id =  %(company_id)s
                    group by account_move_line_id, account_move_id,aml_res.id,acc.id, journal.id,
                    am.company_id,am.move_type,journal.type,journal.code
                    
                UNION ALL
                SELECT
                    coalesce(aml.id) AS account_move_line_id,
                    coalesce(aml_res.id) AS partner_id,
                    coalesce(am.id) AS account_move_id,
                    coalesce(journal.id) AS journal_id,
                    coalesce(acc.id) AS account_id,
                    0.0 as initial_balance,
                    0.0 as debit,
                    0.0 as credit,
                    sum(
                        aml.balance - COALESCE(
                        (
                            SELECT
                            SUM(amount)
                            FROM account_partial_reconcile
                            WHERE
                            debit_move_id = aml.id
                            AND max_date <= %(end_date)s
                        ),0) 
                        + 
                        COALESCE(
                        (SELECT
                         SUM(amount)
                         FROM account_partial_reconcile
                         WHERE credit_move_id = aml.id
                         AND max_date <= %(end_date)s ), 0 )) AS final_balance,
                    am.company_id AS company_id,
                    CASE 
                    WHEN am.move_type = 'out_invoice' THEN 'sale'
                    when am.move_type = 'out_refund' THEN 'credit_memo'
                    when am.move_type = 'entry' AND journal.type = 'bank' THEN 'payment_receipt'
                    when am.move_type = 'entry' AND journal.type = 'general' AND journal.code ilike 'STJ' THEN 'adjustments'
                    ELSE 'misc'
                  END AS transaction_type
                    FROM account_move_line aml
                    LEFT JOIN account_move am ON aml.move_id = am.id
                    LEFT JOIN account_payment ap ON aml.payment_id = ap.id
                    LEFT JOIN res_partner aml_res ON aml.partner_id = aml_res.id
                    LEFT JOIN account_account acc ON aml.account_id = acc.id
                    LEFT JOIN account_payment_term apt ON am.invoice_payment_term_id = apt.id
                    LEFT JOIN account_journal journal  ON journal.id = am.journal_id
                    WHERE
                    acc.account_type IN ('asset_receivable') AND aml.partner_id IS NOT null
                    AND aml.balance <> 0 AND am.state = 'posted'
                    AND aml.date <= %(end_date)s
                    AND aml.company_id =  %(company_id)s
                    group by account_move_line_id, account_move_id,aml_res.id,acc.id, journal.id,
                    am.company_id,am.move_type,journal.type,journal.code
                    
                UNION ALL
                SELECT
                    coalesce(aml.id) AS account_move_line_id,
                    coalesce(aml_res.id) AS partner_id,
                    coalesce(am.id) AS account_move_id,
                    coalesce(journal.id) AS journal_id,
                    coalesce(acc.id) AS account_id,
                    0.0  AS initial_balance,
                    CASE WHEN sum(aml.debit ) > 0 THEN sum(aml.balance) ELSE 0 End AS debit,
                    CASE WHEN sum(aml.credit) > 0 THEN sum(aml.amount_residual) ELSE 0 End AS credit,
                    0.0 as final_balance,
                    am.company_id AS company_id,
                    CASE 
                    WHEN am.move_type = 'out_invoice' THEN 'sale'
                    when am.move_type = 'out_refund' THEN 'credit_memo'
                    when am.move_type = 'entry' AND journal.type = 'bank' THEN 'payment_receipt'
                    when am.move_type = 'entry' AND journal.type = 'general' AND journal.code ilike 'STJ' THEN 'adjustments'
                    ELSE 'misc' END AS transaction_type
                    FROM account_move_line aml
                    LEFT JOIN account_move am ON aml.move_id = am.id
                    LEFT JOIN account_payment ap ON aml.payment_id = ap.id
                    LEFT JOIN res_partner aml_res ON aml.partner_id = aml_res.id
                    LEFT JOIN account_account acc ON aml.account_id = acc.id
                    LEFT JOIN account_payment_term apt ON am.invoice_payment_term_id = apt.id
                    LEFT JOIN account_journal journal  ON journal.id = am.journal_id
                    WHERE
                    acc.account_type IN ('asset_receivable') AND aml.partner_id IS NOT null
                    AND aml.balance <> 0 AND am.state = 'posted'
                    AND aml.date >= %(start_date)s AND aml.date <= %(end_date)s
                    AND am.company_id=  %(company_id)s
                    group by account_move_line_id, account_move_id,aml_res.id,acc.id, journal.id,
                    am.company_id,am.move_type,journal.type,journal.code
                 ) as output 
                 group by account_move_line_id, account_move_id,
                 company_id, account_id,
                 journal_id, partner_id, transaction_type
                """
                self._cr.execute(aging_query, {'uid': uid, 'company_id': company_id,
                                                'end_date':end_date, 'start_date': start_date})

                action = self.env.ref(
                    'flybar_aged_rollup_report.action_aged_receivable_rollup', False)
                action_data = None
                if action:
                    action.update({'name': f"{action.name} (From: {self.date_from} - To: {self.date_to})",
                                   'domain': [('create_uid', '=', uid)],
                                   })
                    action_data = action.sudo().read()[0]
                return action_data

 

class AgedReceivalbeRollup(models.Model):
    _name = 'aged.receivable.rollup'
    _description = 'Aged Receivable Rollup'

    date = fields.Date()
    date_maturity = fields.Date()
    name = fields.Char()
    ref = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    debit = fields.Monetary(string="Debit", currency_field='currency_id')
    credit = fields.Monetary(string="Credit", currency_field='currency_id')
    initial_balance = fields.Monetary(string="Starting Balance", currency_field='currency_id')
    final_balance = fields.Monetary(string="Ending Balance", currency_field='currency_id')
    balance = fields.Monetary(string="Balance", currency_field='currency_id')
    transaction_type = fields.Selection([('sale', 'Sale'),
                             ('payment_receipt', 'Payment Receipt'),
                             ('discount', 'Discounts'),
                             ('adjustments', 'Adjustments'),
                             ('misc', 'Etc'),
                             ('credit_memo', 'Credit Memo')], string='Type')
    account_move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    account_move_line_id = fields.Many2one('account.move.line', string='Journal Item', readonly=True)