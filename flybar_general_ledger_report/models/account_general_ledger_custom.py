# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class GeneralLedgerWizard(models.TransientModel):
    _name = 'general.ledger.report.wizard'
    _description = 'General Ledger Report Wizard'

    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To', default=lambda *a: time.strftime('%Y-%m-%d'))
    date_selection_option = fields.Selection([
        ('end_of_last_month', 'Last Month'),
        ('end_of_last_quarter', 'Last Quarter'),
        ('end_of_last_fin_year', 'Last Financial Year'),
        ('custom', 'Custom')], string="Options", default="custom")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('date_selection_option')
    def onchange_date_selection_option(self):
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

    def create_update_general_ledger(self):
        company_id = self.company_id.id
        end_date = self.date_to
        start_date = self.date_from
        journal_ids = self.env['account.journal'].sudo().with_context(active_test=False).search([
                ('company_id', '=',company_id)
            ], order="company_id, name").ids
        if not end_date and not start_date:
            raise ValidationError(_("Please select date to generate the report."))
        uid = self.env.user.id
        self._cr.execute("delete from general_ledger_report_custom where create_uid=%s", [uid])
        if end_date and start_date:
            ledger_query = """
        INSERT INTO general_ledger_report_custom (
            create_date, create_uid, write_date,
            write_uid, account_move_line_id, date, date_maturity,
            name,ref, company_id, account_id,
            payment_id, journal_id, partner_id, currency_id, transaction_type,
            debit, credit, initial_balance, final_balance,
            balance
            )
        SELECT
            now(), %(uid)s, now(), %(uid)s,
            account_move_line_id, date, date_maturity,
            name,ref, company_id, account_id,
            payment_id, journal_id, partner_id, currency_id, transaction_type,
            debit, credit, initial_balance, final_balance,
            balance
        FROM
          (
            WITH ledger AS
                (
                (SELECT
                    account_move_line.id as account_move_line_id,
                    account_move_line.date as date,
                    account_move_line.date_maturity as date_maturity,
                    account_move_line.name as name,
                    account_move_line.ref as ref,
                    account_move_line.company_id as company_id,
                    account_move_line.account_id as account_id,
                    account_move_line.payment_id as payment_id,
                    account_move_line.journal_id as journal_id,
                    account_move_line.partner_id as partner_id,  
                    account_move_line.currency_id as currency_id,  
                    CASE 
                        WHEN account_move_line.is_discount = TRUE THEN 'discount'
                        WHEN move.move_type = 'out_invoice' THEN 'sale'
                        when move.move_type = 'out_refund' THEN 'credit_memo'
                        WHEN move.move_type = 'in_invoice' THEN 'bill'
 						WHEN move.move_type = 'in_refund' THEN 'bill_refund'
                        WHEN move.move_type = 'entry' AND journal.type = 'bank' AND payment.partner_type = 'customer' THEN 'customer_payment_receipt'
 						WHEN move.move_type = 'entry' AND journal.type = 'bank' AND payment.partner_type = 'supplier' THEN 'supplier_payment_receipt'
                        WHEN move.move_type = 'entry' AND journal.type = 'general' AND journal.code ilike 'STJ' THEN 'misc'
                        ELSE 'adjustments'
                    END AS transaction_type,
                    case when account_move_line.date <= %(end_date)s and account_move_line.date >= %(start_date)s
                        then sum(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)) else 0 end AS debit,
                    case when account_move_line.date <= %(end_date)s and account_move_line.date >= %(start_date)s
                        then sum(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)) else 0 end  AS credit,
                    case when account_move_line.date < %(start_date)s
                        then sum(ROUND((account_move_line.debit - account_move_line.credit) * currency_table.rate, currency_table.precision)) else 0 end as initial_balance,

                    case when account_move_line.date <= %(end_date)s
                        then sum(ROUND((account_move_line.debit - account_move_line.credit) * currency_table.rate, currency_table.precision)) else 0 end as final_balance,

                    case when account_move_line.date <= %(end_date)s and account_move_line.date >= %(start_date)s
                        then sum(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) else 0 end AS balance
                    FROM "account_move_line"
                    JOIN account_move move ON move.id = account_move_line.move_id
                    LEFT JOIN (VALUES (%(company_id)s, 1.0, 2)) AS currency_table(company_id, rate, precision) ON currency_table.company_id = account_move_line.company_id
                    LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                    LEFT JOIN account_payment payment           ON payment.move_id = move.id
                    WHERE (((((("account_move_line"."display_type" not in ('line_section', 'line_note')) 
                                 OR "account_move_line"."display_type" IS NULL) 
                                 AND ("account_move_line"."company_id" = %(company_id)s)) 
                                 AND ("account_move_line"."journal_id" in %(journal_ids)s))    
                                 AND ("account_move_line"."date" <= %(end_date)s))
                                 AND ("account_move_line"."parent_state" = 'posted')) 
                                 AND ("account_move_line"."company_id" IS NULL  OR ("account_move_line"."company_id" = %(company_id)s))
                    group BY account_move_line.id, move.move_type, payment.partner_type, journal.code, journal.type ,account_move_line.date, currency_table.rate, currency_table.precision)
                ) 
            SELECT
                ledger.account_move_line_id, max(ledger.date) as date, max(ledger.date_maturity) as date_maturity,
                max(ledger.name) as name, max(ledger.ref) as ref, max(ledger.company_id) as company_id, max(ledger.account_id) as account_id,
                max(ledger.payment_id) as payment_id, max(ledger.journal_id) as journal_id, max(ledger.partner_id) as partner_id, max(ledger.currency_id) as currency_id, max(transaction_type) as transaction_type, sum(ledger.debit) as debit, sum(ledger.credit) as credit,
                sum(ledger.initial_balance) as initial_balance, sum(ledger.final_balance) as final_balance, sum(ledger.balance) as balance
	        from ledger
	        group by ledger.account_move_line_id
          ) AS output
            """
            self._cr.execute(ledger_query, {'uid': uid, 'company_id': company_id, 'journal_ids': tuple(journal_ids),
                                            'end_date':end_date, 'start_date': start_date})
            action = self.env.ref(
                'flybar_general_ledger_report.action_general_ledger', False)
            action_data = None
            if action:
                action.update({'name': f"{action.name} (From: {self.date_from} - To: {self.date_to})",
                               'domain': [('create_uid', '=', uid)],
                               })
                action_data = action.sudo().read()[0]
            return action_data


class GeneralLedgerCustom(models.Model):
    _name = 'general.ledger.report.custom'
    _description = 'General Ledger Custom'

    date = fields.Date()
    date_maturity = fields.Date()
    name = fields.Char()
    ref = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal')
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    debit = fields.Monetary(string="Debit", currency_field='currency_id')
    credit = fields.Monetary(string="Credit", currency_field='currency_id')
    initial_balance = fields.Monetary(string="Starting Balance", currency_field='currency_id')
    final_balance = fields.Monetary(string="Ending Balance", currency_field='currency_id')
    balance = fields.Monetary(string="Balance", currency_field='currency_id')
    transaction_type = fields.Selection([('sale', 'Sale'),
                             ('customer_payment_receipt', 'Customer Payment Receipt'),
                             ('supplier_payment_receipt', 'Supplier Payment Receipt'),
                             ('discount', 'Discounts'),
                             ('adjustments', 'Adjustments'),
                             ('bill', 'Bill'),
                             ('bill_refund', 'Bill Refund'),
                             ('misc', 'Etc'),
                             ('credit_memo', 'Credit Memo')], string='Type')
    account_move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    account_move_line_id = fields.Many2one('account.move.line', string='Journal Item', readonly=True)


    def create_update_ledger(self):
        return self.env['general.ledger.report.wizard'
                        ].create_update_general_ledger()


    def cron_remove_data(self):
        self._cr.execute("""
                    DELETE FROM general_ledger_report_custom
                    WHERE create_date < (NOW() - INTERVAL '24 HOURS')
                    """)

