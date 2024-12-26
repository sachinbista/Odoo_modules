# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models, tools
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

class AccountAgedPayable(models.TransientModel):
    _name = 'account.payable.report.wizard'
    _description = 'Account Payable Details Report'

    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    date_selection_option = fields.Selection([
        ('end_of_last_month', 'End of Last Month'),
        ('end_of_last_quarter', 'End of Last Quarter'),
        ('end_of_last_fin_year', 'End of Last Financial Year'),
        ('custom', 'Custom')], string="Options", default="custom")

    @api.onchange('date_selection_option')
    def onchange_date_selection_option(self):
        if self.date_selection_option == 'end_of_last_month':
            today = date.today()
            first = today.replace(day=1)
            last_month = first - timedelta(days=1)
            self.date_from = last_month
        if self.date_selection_option == 'end_of_last_quarter':
            first_month_of_quarter = ((datetime.now().month - 1) // 3) * 3 + 1
            date_from = datetime.now().replace(
                month=first_month_of_quarter, day=1) - relativedelta(days=1)
            self.date_from = date_from.date()
        if self.date_selection_option == 'end_of_last_fin_year':
            today = date.today()
            year = today.year
            self.date_from = today.replace(month=12, day=31, year=year - 1)
        if self.date_selection_option == 'custom':
            self.date_from = date.today()

    def create_update_customer_aging(self):
        payable_report_obj = self.env['account.payable.report'].search([])
        payable_report_obj.create_update_customer_aging(self.date_from)
        action = self.env.ref(
            'flybar_payable_report.action_account_payable_aging', False)
        action_data = None
        if action:
            action_data = action.sudo().read()[0]
        return action_data


class AccountPayableReport(models.Model):
    _name = 'account.payable.report'
    _rec_name = 'partner_id'
    _description = 'Account Payable Report'

    partner_id = fields.Many2one(
        'res.partner', string='Vendor', readonly=True)
    purchase_order_id = fields.Many2one(
        'purchase.order', string='Purchase Order', readonly=True)
    source_document = fields.Char(string='Source Document', readonly=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Term', readonly=True)
    account_move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True)
    account_move_line_id = fields.Many2one(
        'account.move.line', string='Journal Item', readonly=True)
    accounting_date = fields.Date(string='Accounting Date', readonly=True)
    bill_date = fields.Date(string='Bill Date', readonly=True)
    date_maturity = fields.Date(string='Due Date', readonly=True)
    bucket_current = fields.Monetary(string='Current', readonly=True)
    bucket_30 = fields.Monetary(string='1-30 Days', readonly=True)
    bucket_60 = fields.Monetary(string='31-60 Days', readonly=True)
    bucket_90 = fields.Monetary(string='61-90 Days', readonly=True)
    bucket_120 = fields.Monetary(string='91-120 Days', readonly=True)
    bucket_150 = fields.Monetary(string='121-150 Days', readonly=True)
    bucket_180 = fields.Monetary(string='151-180 Days', readonly=True)
    bucket_180_plus = fields.Monetary(string='Plus 180 Days', readonly=True)
    balance = fields.Monetary(string='Total', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True)
    currency_id = fields.Many2one(
        related="company_id.currency_id", string="Currency", readonly=True)

    @api.model
    def create_update_customer_aging(self, as_of_date=False):
        self._cr.execute("delete from account_payable_report")
        uid = self.env.user.id
        as_of_date = as_of_date if as_of_date else date.today()
        customer_query = """
        INSERT INTO account_payable_report (
            create_date, create_uid, write_date,
            write_uid, partner_id,
            account_move_id,account_move_line_id,
            source_document, payment_term_id,
            accounting_date, bill_date, date_maturity,
            bucket_current, bucket_30, bucket_60,
            bucket_90, bucket_120, bucket_150,
            bucket_180, bucket_180_plus, balance,
            company_id
            )
        SELECT
            now(),
            %s,
            now(),
            %s,
            partner_id,
            account_move_id,
            account_move_line_id,
            source_document,
            payment_term_id,
            accounting_date,
            bill_date,
            date_maturity,
            bucket_current,
            bucket_30,
            bucket_60,
            bucket_90,
            bucket_120,
            bucket_150,
            bucket_180,
            bucket_180_plus,
            balance,
            company_id
        FROM
          (
            WITH aged AS (
                SELECT
                    partner_id,
                    account_move_id,
                    account_move_line_id,
                    source_document,
                    payment_term_id,
                    accounting_date,
                    bill_date,
                    date_maturity,
                    company_id,
                    bucket_current,
                    bucket_30,
                    bucket_60,
                    bucket_90,
                    bucket_120,
                    bucket_150,
                    bucket_180,
                    bucket_180_plus,
                    amt AS balance
                FROM (
                    SELECT
                        partner_id,
                        account_move_id,
                        account_move_line_id,
                        
                        source_document,
                        payment_term_id,
                        accounting_date,
                        bill_date,
                        date_maturity,
                        amt AS amt,
                        orig_amt AS orig_amt,
                        company_id,
                        CASE WHEN
                            date_maturity >= aged_date THEN amt ELSE 0
                        END bucket_current,
                        CASE WHEN (date_maturity < aged_date)
                        AND (
                            date_maturity >= (aged_date - interval '30 days')
                        ) THEN amt ELSE 0 end bucket_30,
                        CASE WHEN (
                            date_maturity < (aged_date - interval '30 days')
                            )
                        AND (
                          date_maturity >= (aged_date - interval '60 days')
                        ) THEN amt ELSE 0 END bucket_60,
                        CASE WHEN (
                          date_maturity < (aged_date - interval '60 days')
                        )
                        AND (
                            date_maturity >= (aged_date - interval '90 days')
                        ) THEN amt ELSE 0 END bucket_90,
                        CASE WHEN (
                            date_maturity < (aged_date - interval '90 days')
                        )
                        AND (
                            date_maturity >= (aged_date - interval '120 days')
                        ) THEN amt ELSE 0 END bucket_120,
                        CASE WHEN (
                            date_maturity < (aged_date - interval '120 days')
                        )
                        AND (
                            date_maturity >= (aged_date - interval '150 days')
                        ) THEN amt ELSE 0 END bucket_150,
                        CASE WHEN (
                            date_maturity < (aged_date - interval '150 days')
                        )
                        AND (
                            date_maturity >= (aged_date - interval '180 days')
                        ) THEN amt ELSE 0 END bucket_180,
                        CASE WHEN (
                            date_maturity < (aged_date - interval '180 days')
                        ) THEN amt ELSE 0 END bucket_180_plus
                    FROM
                    (
                        SELECT
                            coalesce(aml_res.id) AS partner_id,
                            coalesce(am.id) AS account_move_id,
                            coalesce(aml.id) AS account_move_line_id,
                            coalesce(am.invoice_origin, aml.ref) AS source_document,
                            apt.id AS payment_term_id,
                            (
                                aml.balance - COALESCE(
                                (
                                    SELECT
                                        SUM(amount)
                                    FROM
                                        account_partial_reconcile
                                    WHERE
                                    debit_move_id = aml.id
                                    AND max_date <= %s
                                ),
                                0
                                ) + COALESCE(
                                (
                                    SELECT
                                        SUM(amount)
                                    FROM
                                        account_partial_reconcile
                                    WHERE
                                    credit_move_id = aml.id
                                    AND max_date <= %s
                                ),
                                0
                                )
                            ) AS amt,
                            aml.amount_residual AS orig_amt,
                            %s AS aged_date,
                            (now() at time zone 'UTC')::date - aml.date_maturity::date
                            AS diff_date,
                            am.invoice_date :: date AS bill_date,
                            aml.date_maturity :: date AS date_maturity,
                            coalesce(am.date, aml.date) AS accounting_date,
                            am.company_id AS company_id
                        FROM
                        account_move_line aml
                        LEFT JOIN account_move am
                            ON aml.move_id = am.id
                        LEFT JOIN account_payment ap
                            ON aml.payment_id = ap.id
                        LEFT JOIN res_partner aml_res
                            ON aml.partner_id = aml_res.id
                        LEFT JOIN account_account acc
                            ON aml.account_id = acc.id
                        LEFT JOIN account_payment_term apt
                            ON am.invoice_payment_term_id = apt.id
                        WHERE
                        acc.account_type IN ('liability_payable')
                        AND aml.partner_id IS NOT null
                        AND aml.balance <> 0
                        AND am.state = 'posted'
                        AND aml.date <= %s
                    ) AS record
                    WHERE
                    record.amt <> 0
                    ORDER BY
                    record.partner_id
                ) AS result
              ORDER BY
                partner_id
            )
            SELECT
                aged.partner_id,
                aged.account_move_id,
                aged.account_move_line_id,
                aged.source_document,
                aged.payment_term_id,
                aged.accounting_date,
                aged.bill_date,
                aged.date_maturity,
                aged.company_id,
                aged.bucket_current,
                aged.bucket_30,
                aged.bucket_60,
                aged.bucket_90,
                aged.bucket_120,
                aged.bucket_150,
                aged.bucket_180,
                aged.bucket_180_plus,
                aged.balance
            FROM
              aged
            ORDER BY
              aged.partner_id
          ) AS output
            """
        self._cr.execute(customer_query, [
            uid, uid, as_of_date, as_of_date, as_of_date, as_of_date])
        action = self.env.ref('flybar_payable_report.action_account_payable_aging', False)
        action.sudo().context = {'search_default_company_id': self.env.user.company_id.id}
        action_data = None
        if action:
            action_data = action.read()[0]
        return action_data