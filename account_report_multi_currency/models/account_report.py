# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import api, fields, models


class AccountReport(models.Model):
    _inherit = 'account.report'

    curr_conversation = fields.Boolean(
        compute="_compute_curr_conversation",
        precompute=True,
        store=True,
        readonly=False,
        string='Currency Conversation')
    curr_currency_id = fields.Many2one('res.currency', string='Currency')

    @api.onchange("curr_conversation")
    def _onchange_curr_conversation(self):
        for acc_report in self:
            if not acc_report.curr_conversation:
                acc_report.curr_currency_id = False


    @api.depends("curr_conversation")
    def _compute_curr_conversation(self):
        for acc_report in self:
            if not acc_report.curr_conversation:
                acc_report.curr_currency_id = False

    @api.model
    def format_value(self, options, value, currency=False, blank_if_zero=False, figure_type=None, digits=1):
        if self.curr_currency_id:
            currency = self.curr_currency_id
        if not self:
            currency = self.env['account.report'].browse(self.env.context.get('report_id')).curr_currency_id
        formatted_amount = super(AccountReport, self).format_value(value=value, options=options, currency=currency, blank_if_zero=blank_if_zero, figure_type=figure_type, digits=digits)
        return formatted_amount

    def export_to_pdf(self, options):
        print_mode_self = self.with_context(print_mode=True, report_id=self.id)
        return super(AccountReport, print_mode_self).export_to_pdf(options=options)

    def _get_rounding_unit_names(self):
        currency_symbol = self.env.company.currency_id.symbol
        if self.curr_currency_id:
            currency_symbol = self.curr_currency_id.symbol
        rounding_unit_names = [
            ('decimals', '.%s' % currency_symbol),
            ('units', '%s' % currency_symbol),
            ('thousands', 'K%s' % currency_symbol),
            ('millions', 'M%s' % currency_symbol),
        ]

        # We want to add 'lakhs' for Indian Rupee
        if (self.env.company.currency_id == self.env.ref('base.INR')):
            # We want it between 'thousands' and 'millions'
            rounding_unit_names.insert(3, ('lakhs', 'L%s' % currency_symbol))

        return dict(rounding_unit_names)

    def _build_column_dict(self, col_value, col_data, options=None, currency=False, digits=1, column_expression=None, has_sublines=False, report_line_id=None):
        if self.curr_currency_id:
            currency = self.curr_currency_id
        res = super(AccountReport, self)._build_column_dict(col_value=col_value,col_data=col_data,options=options,currency=currency,digits=digits, column_expression=column_expression, has_sublines=has_sublines,report_line_id=report_line_id)
        return res


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _get_query_currency_table(self, company_ids, conversion_date):
        ''' Construct the currency table as a mapping company -> rate to convert the amount to the user's company
        currency in a multi-company/multi-currency environment.
        The currency_table is a small postgresql table construct with VALUES.
        :param options: The report options.
        :return:        The query representing the currency table.
        '''
        report_id = self.env.context.get('report_id')
        user_company = self.env.company
        user_currency = user_company.currency_id
        if report_id:
            report = self.env['account.report'].browse(report_id)
            if report.curr_currency_id:
                user_currency = report.curr_currency_id

        companies = self.env['res.company'].browse(company_ids)
        currency_rates = self.env['res.currency'].search([])._get_rates(user_company, conversion_date)
        conversion_rates = []
        for company in companies:
            conversion_rates.extend((
                company.id,
                currency_rates[user_currency.id] / currency_rates[company.currency_id.id],
                user_currency.decimal_places,
            ))
        query = '(VALUES %s) AS currency_table(company_id, rate, precision)' % ','.join('(%s, %s, %s)' for i in companies)
        return self.env.cr.mogrify(query, conversion_rates).decode(self.env.cr.connection.encoding)