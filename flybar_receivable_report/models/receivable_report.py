# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class AccountAgedReceivable(models.TransientModel):
    _name = 'account.receivable.report.wizard'
    _description = 'Account Receivable Details Report'

    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    date_selection_option = fields.Selection([
        ('end_of_last_month', 'End of Last Month'),
        ('end_of_last_quarter', 'End of Last Quarter'),
        ('end_of_last_fin_year', 'End of Last Financial Year'),
        ('custom', 'Custom')], string="Options", default="custom")
    receivable_at = fields.Selection([('due_date', 'Due Date'),
                                      ('invoice_date', 'Invoice Date')], string="Receivable at", default="due_date")

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
        as_of_date = self.date_from if self.date_from else date.today()
        if not as_of_date:
            raise ValidationError(_("Please select date to generate the report."))
        uid = self.env.user.id
        self._cr.execute("delete from account_receivable_report where create_uid=%s", [uid])
        if self.receivable_at != 'invoice_date':
            customer_query = """
        INSERT INTO account_receivable_report (
            create_date, create_uid, write_date,
            write_uid, partner_id, salesperson_id,
            account_move_id,account_move_line_id, sale_order_id, warehouse_id,
            source_document, type, payment_term_id,
            accounting_date, bill_date, date_maturity,
            bucket_current, bucket_30, bucket_60,
            bucket_90, bucket_120, bucket_150,
            bucket_180, bucket_180_plus, balance,
            original_bal, tax_amt, company_id
            )
        SELECT
            now(),
            %s,
            now(),
            %s,
            partner_id,
            salesperson_id,
            account_move_id,
            account_move_line_id,
            sale_order_id,
            warehouse_id,
            source_document,
            type,
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
            original_bal,
            tax_amt,
            company_id
        FROM
          (
            WITH aged AS (
                SELECT
                    partner_id,
                    salesperson_id,
                    account_move_id,
                    account_move_line_id,
                    sale_order_id,
                    (
                        SELECT
                            DISTINCT warehouse_id
                        FROM
                            sale_order
                        WHERE
                            id = sale_order_id
                        LIMIT
                            1
                    ) AS warehouse_id,
                    source_document,
                    type,
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
                    amt AS balance,
                    orig_amt AS original_bal,
                    tax_amt AS tax_amt
                FROM
                (
                    SELECT
                        partner_id,
                        salesperson_id,
                        account_move_id,
                        account_move_line_id,
                        (
                            SELECT
                                DISTINCT so.id
                            FROM
                                account_move am
                                LEFT JOIN account_move_line aml
                                    ON aml.move_id = am.id
                                LEFT JOIN sale_order_line_invoice_rel solr
                                    ON solr.invoice_line_id = aml.id
                                LEFT JOIN sale_order so ON so.id = (
                                    SELECT
                                        order_id
                                    FROM
                                        sale_order_line
                                    WHERE
                                        id = solr.order_line_id
                                    )
                            WHERE
                                am.id = record.account_move_id
                            LIMIT
                                1
                        ) AS sale_order_id,
                        source_document,
                        type,
                        payment_term_id,
                        accounting_date,
                        bill_date,
                        date_maturity,
                        amt AS amt,
                        orig_amt AS orig_amt,
                        (
                        SELECT
                            sum(taml.balance) * -1
                        FROM
                            account_move_line taml
                            LEFT JOIN account_move tam ON tam.id = taml.move_id
                        WHERE
                            taml.tax_line_id IS NOT NULL
                            AND tam.id = account_move_id
                        ) AS tax_amt,
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
                            coalesce(am.invoice_user_id) AS salesperson_id,
                            coalesce(am.id) AS account_move_id,
                            coalesce(aml.id) AS account_move_line_id,
                            coalesce(am.invoice_origin, aml.ref) AS source_document,
                            CASE 
                                WHEN am.move_type = 'out_invoice' THEN 'sale'
                                when am.move_type = 'out_refund' THEN 'credit_memo'
                                when am.move_type = 'entry' AND aj.type = 'bank' THEN 'payment_receipt'
                                ELSE 'misc'
                            END AS type,
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
                        LEFT JOIN account_journal aj
	                        ON am.journal_id = aj.id
                        WHERE
                        acc.account_type IN ('asset_receivable')
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
                aged.salesperson_id,
                aged.account_move_id,
                aged.account_move_line_id,
                aged.sale_order_id,
                aged.warehouse_id,
                aged.source_document,
                aged.payment_term_id,
                aged.type,
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
                aged.balance,
                aged.original_bal,
                aged.tax_amt
            FROM
              aged
            ORDER BY
              aged.partner_id
          ) AS output
    
            """
            self._cr.execute(customer_query, [
                uid, uid, as_of_date, as_of_date, as_of_date, as_of_date])
            action = self.env.ref(
                'flybar_receivable_report.action_account_receivable_aging', False)
            action_data = None
            if action:
                action_data = action.sudo().read()[0]
            return action_data
        else:
            customer_query = """
                    INSERT INTO account_receivable_report (
                        create_date, create_uid, write_date,
                        write_uid, partner_id, salesperson_id,
                        account_move_id, sale_order_id, warehouse_id,
                        source_document,type, payment_term_id,
                        accounting_date, bill_date,
                        bucket_current, bucket_30, bucket_60,
                        bucket_90, bucket_120, bucket_150,
                        bucket_180, bucket_180_plus, balance,
                        original_bal, tax_amt, company_id
                    )
                    SELECT
                        now(),
                        %s,
                        now(),
                        %s,
                        partner_id,
                        salesperson_id,
                        account_move_id,
                        sale_order_id,
                        warehouse_id,
                        source_document,
                        type,
                        payment_term_id,
                        accounting_date,
                        bill_date,
                        bucket_current,
                        bucket_30,
                        bucket_60,
                        bucket_90,
                        bucket_120,
                        bucket_150,
                        bucket_180,
                        bucket_180_plus,
                        balance,
                        original_bal,
                        tax_amt,
                        company_id
                    FROM
                      (
                        WITH aged AS (
                            SELECT
                                partner_id,
                                salesperson_id,
                                account_move_id,
                                sale_order_id,
                                (
                                    SELECT
                                        DISTINCT warehouse_id
                                    FROM
                                        sale_order
                                    WHERE
                                        id = sale_order_id
                                    LIMIT
                                        1
                                ) AS warehouse_id,
                                source_document,
                                type,
                                payment_term_id,
                                accounting_date,
                                bill_date,
                                company_id,
                                bucket_current,
                                bucket_30,
                                bucket_60,
                                bucket_90,
                                bucket_120,
                                bucket_150,
                                bucket_180,
                                bucket_180_plus,
                                amt AS balance,
                                orig_amt AS original_bal,
                                tax_amt AS tax_amt
                            FROM
                            (
                                SELECT
                                    partner_id,
                                    salesperson_id,
                                    account_move_id,
                                    (
                                        SELECT
                                            DISTINCT so.id
                                        FROM
                                            account_move am
                                            LEFT JOIN account_move_line aml
                                                ON aml.move_id = am.id
                                            LEFT JOIN sale_order_line_invoice_rel solr
                                                ON solr.invoice_line_id = aml.id
                                            LEFT JOIN sale_order so ON so.id = (
                                                SELECT
                                                    order_id
                                                FROM
                                                    sale_order_line
                                                WHERE
                                                    id = solr.order_line_id
                                                )
                                        WHERE
                                            am.id = record.account_move_id
                                        LIMIT
                                            1
                                    ) AS sale_order_id,
                                    source_document,
                                    type,
                                    payment_term_id,
                                    accounting_date,
                                    bill_date,
                                    amt AS amt,
                                    orig_amt AS orig_amt,
                                    (
                                    SELECT
                                        sum(taml.balance) * -1
                                    FROM
                                        account_move_line taml
                                        LEFT JOIN account_move tam ON tam.id = taml.move_id
                                    WHERE
                                        taml.tax_line_id IS NOT NULL
                                        AND tam.id = account_move_id
                                    ) AS tax_amt,
                                    company_id,
                                    CASE WHEN
                                        invoiced_date >= aged_date THEN amt ELSE 0
                                    END bucket_current,
                                    CASE WHEN (invoiced_date < aged_date)
                                    AND (
                                        invoiced_date >= (aged_date - interval '30 days')
                                    ) THEN amt ELSE 0 end bucket_30,
                                    CASE WHEN (
                                        invoiced_date < (aged_date - interval '30 days')
                                        )
                                    AND (
                                      invoiced_date >= (aged_date - interval '60 days')
                                    ) THEN amt ELSE 0 END bucket_60,
                                    CASE WHEN (
                                      invoiced_date < (aged_date - interval '60 days')
                                    )
                                    AND (
                                        invoiced_date >= (aged_date - interval '90 days')
                                    ) THEN amt ELSE 0 END bucket_90,
                                    CASE WHEN (
                                        invoiced_date < (aged_date - interval '90 days')
                                    )
                                    AND (
                                        invoiced_date >= (aged_date - interval '120 days')
                                    ) THEN amt ELSE 0 END bucket_120,
                                    CASE WHEN (
                                        invoiced_date < (aged_date - interval '120 days')
                                    )
                                    AND (
                                        invoiced_date >= (aged_date - interval '150 days')
                                    ) THEN amt ELSE 0 END bucket_150,
                                    CASE WHEN (
                                        invoiced_date < (aged_date - interval '150 days')
                                    )
                                    AND (
                                        invoiced_date >= (aged_date - interval '180 days')
                                    ) THEN amt ELSE 0 END bucket_180,
                                    CASE WHEN (
                                        invoiced_date < (aged_date - interval '180 days')
                                    ) THEN amt ELSE 0 END bucket_180_plus
                                FROM
                                (
                                    SELECT
                                        coalesce(aml_res.id) AS partner_id,
                                        coalesce(am.invoice_user_id) AS salesperson_id,
                                        coalesce(am.id) AS account_move_id,
                                        coalesce(am.invoice_origin, aml.ref) AS source_document,
                                        CASE 
                                            WHEN am.move_type = 'out_invoice' THEN 'sale'
                                            when am.move_type = 'out_refund' THEN 'credit_memo'
                                            when am.move_type = 'entry' AND aj.type = 'bank' THEN 'payment_receipt'
                                            ELSE 'misc'
                                        END AS type,
                                        apt.id AS payment_term_id,
                                        sum(
                                            aml.balance - COALESCE(
                                            (
                                                SELECT
                                                SUM(amount)
                                                FROM account_partial_reconcile
                                                WHERE
                                                debit_move_id = aml.id
                                                AND max_date <= %s
                                            ),0) 
                                            + 
                                            COALESCE(
                                            (SELECT
                                             SUM(amount)
                                             FROM account_partial_reconcile
                                             WHERE credit_move_id = aml.id
                                             AND max_date <= %s ), 0 )) AS amt,
                                        sum(aml.amount_residual) AS orig_amt,
                                        %s AS aged_date,
                                        max(am.invoice_date:: date) AS bill_date,
                                        max(coalesce(am.date, aml.date)) AS accounting_date,
                                        max(coalesce(am.date, aml.date)) AS invoiced_date,
                                        am.company_id AS company_id
                                        FROM account_move_line aml
                                        LEFT JOIN account_move am ON aml.move_id = am.id
                                        LEFT JOIN account_payment ap ON aml.payment_id = ap.id
                                        LEFT JOIN res_partner aml_res ON aml.partner_id = aml_res.id
                                        LEFT JOIN account_account acc ON aml.account_id = acc.id
                                        LEFT JOIN account_payment_term apt ON am.invoice_payment_term_id = apt.id
                                        LEFT JOIN account_journal aj ON am.journal_id = aj.id
                                        WHERE
                                        acc.account_type IN ('asset_receivable') AND aml.partner_id IS NOT null
                                        AND aml.balance <> 0 AND am.state = 'posted'
                                        AND aml.date <= %s
                                        group by account_move_id, aml_res.id, salesperson_id, payment_term_id, source_document,
                                        am.company_id, am.move_type, aj.type
                                ) AS record
                                WHERE
                                record.amt <> 0
                                GROUP BY record.account_move_id, record.partner_id, record.salesperson_id, record.source_document, record.payment_term_id,
                                record.accounting_date,record.bill_date, record.company_id, record.amt, record.orig_amt, record.invoiced_date, 
                                record.aged_date, record.type
                            ) AS result
                          ORDER BY
                            partner_id
                        )
                        SELECT
                            aged.partner_id,
                            aged.salesperson_id,
                            aged.account_move_id,
                            aged.sale_order_id,
                            aged.warehouse_id,
                            aged.source_document,
                            aged.type,
                            aged.payment_term_id,
                            aged.accounting_date,
                            aged.bill_date,
                            aged.company_id,
                            aged.bucket_current,
                            aged.bucket_30,
                            aged.bucket_60,
                            aged.bucket_90,
                            aged.bucket_120,
                            aged.bucket_150,
                            aged.bucket_180,
                            aged.bucket_180_plus,
                            aged.balance,
                            aged.original_bal,
                            aged.tax_amt
                        FROM
                          aged
                        ORDER BY
                          aged.partner_id
                      ) AS output

                        """
            self._cr.execute(customer_query, [
                uid, uid, as_of_date, as_of_date, as_of_date, as_of_date])
            action = self.env.ref(
                'flybar_receivable_report.action_account_receivable_aging', False)
            action_data = None
            if action:
                action_data = action.sudo().read()[0]
            return action_data


class AccountReceivableReport(models.Model):
    _name = 'account.receivable.report'
    _rec_name = 'partner_id'
    _description = 'Account Receivable Report'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True)
    salesperson_id = fields.Many2one(
        'res.users', string='Salesperson', readonly=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string="Source Warehouse", readonly=True)
    source_document = fields.Char(string='Source Document', readonly=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Term', readonly=True)
    account_move_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True)
    account_move_line_id = fields.Many2one(
        'account.move.line', string='Journal Item', readonly=True)
    accounting_date = fields.Date(string='Accounting Date', readonly=True)
    bill_date = fields.Date(string='Invoice Date', readonly=True)
    date_maturity = fields.Date(string='Due Date', readonly=True)
    bucket_current = fields.Monetary(string='Current', readonly=True)
    bucket_30 = fields.Monetary(string='1-30 Days', readonly=True)
    bucket_60 = fields.Monetary(string='31-60 Days', readonly=True)
    bucket_90 = fields.Monetary(string='61-90 Days', readonly=True)
    bucket_120 = fields.Monetary(string='91-120 Days', readonly=True)
    bucket_150 = fields.Monetary(string='121-150 Days', readonly=True)
    bucket_180 = fields.Monetary(string='151-180 Days', readonly=True)
    bucket_180_plus = fields.Monetary(string='Plus 180 Days', readonly=True)
    balance = fields.Monetary(string='Amount Due', readonly=True)
    original_bal = fields.Monetary(string='Total', readonly=True)
    tax_amt = fields.Monetary(string='Tax', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', readonly=True)
    currency_id = fields.Many2one(
        related="company_id.currency_id", string="Currency", readonly=True)
    credit_limit = fields.Float(string='Credit Limit')
    type = fields.Selection([('sale', 'Sale'),
                             ('payment_receipt', 'Payment Receipt'),
                             ('discounts', 'Discounts'),
                             ('adjustments', 'Adjustments'),
                             ('misc', 'Etc'),
                             ('credit_memo', 'Credit Memo')], string='Type')

    # def action_open_receivable_date(self):
    #     return {
    #         'res_model': 'account.receivable.report.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'type': 'ir.actions.act_window',
    #     }

    def create_update_customer_aging(self):
        return self.env['account.receivable.report.wizard'
                        ].create_update_customer_aging()

    def action_register_payments(self):
        payment_method_notes = ",".join([
            p.payment_method_note or '' for p in self.mapped('partner_id')])

        if any(self.mapped('account_move_id').filtered(
                lambda m: m.move_type == 'entry')):
            payable_type_id = self.env.ref('account.data_account_type_receivable')
            line_ids = self.mapped('account_move_id.line_ids').filtered(
                lambda l: l.account_id.user_type_id.id == payable_type_id.id)
            return {
                'type': 'ir.actions.client',
                'name': _('Reconcile'),
                'tag': 'manual_reconciliation_view',
                'binding_model_id': self.env[
                    'ir.model.data']._xmlid_to_res_id(
                        'account.model_account_move_line'),
                'binding_type': 'action',
                'binding_view_types': 'list',
                'context': {
                    'active_ids': line_ids.ids,
                    'active_model': 'account.move.line'},
            }
        else:
            partners = list(set([each.partner_id.id for each in self]))
            return {
                'name': _('Register Payment'),
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'context': {
                    'active_model': 'account.move',
                    'active_ids': self.account_move_id.ids,
                    'default_payment_method_note': payment_method_notes,
                    'from_receivable_report': True,
                    'create_draft_payment': True,
                    'display_notes': True if len(partners) == 1 else False
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
            }

    def cron_remove_data(self):
        self._cr.execute("""
                    DELETE FROM account_payable_report
                    WHERE create_date < (NOW() - INTERVAL '24 HOURS')
                    """)

    def get_aml_ids(self, field_name, domain):
        """Returns account move line ids to be passed to open journal item view from aging report groupby amt click"""
        domain.append((field_name, '!=', 0))
        if field_name == 'tax_amt':
            aml_ids = self.env['account.receivable.report'].search(domain).account_move_id.line_ids.filtered(lambda r: r.tax_line_id).ids
        else:
            aml_ids = self.env['account.receivable.report'].search(domain).account_move_id.line_ids.filtered(lambda r: r.account_type == 'asset_receivable').ids
        return aml_ids
