# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
import logging

from odoo import models, fields, _
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

class BankReconciliationReportCustomHandler(models.AbstractModel):
    _inherit = 'account.bank.reconciliation.report.handler'

    def _get_statement_report_lines(self, report, options, journal):
        ''' Retrieve the journal items used by the statement lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        report_currency = journal_currency or company_currency
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        if not journal.default_account_id:
            return [], []

        plus_report_lines = []
        less_report_lines = []
        plus_totals = {column['column_group_key']: 0.0 for column in options['columns']}
        less_totals = {column['column_group_key']: 0.0 for column in options['columns']}

        grouped_results = {}
        query, params = self._get_statement_lines_query(report, options, journal)
        self._cr.execute(query, params)


        for results in self._cr.dictfetchall():
            grouped_results.setdefault(results['id'], {})[results['column_group_key']] = results

        for st_line_id, column_group_results in grouped_results.items():

            columns = []
            line_amounts = {}
            move_name = None
            st_line_id = None

            for column in options['columns']:

                col_expr_label = column['expression_label']
                results = column_group_results.get(column['column_group_key'], {})
                line_amounts[column['column_group_key']] = 0.0

                if col_expr_label == 'label':
                    col_value = results and report._format_aml_name(results['payment_ref'], results['ref'], '/') or None
                else:
                    col_value = results.get(col_expr_label)

                if col_expr_label == 'vendor_name':
                    col_value = self.env['account.bank.statement.line'].browse(results.get('id')).partner_id.name
                else:
                    col_value = results.get(col_expr_label)
                #
                # if col_expr_label == 'vendor_name':
                #     col_value = self.env['account.bank.statement.line'].browse(results.get('id')).partner_id.name
                # else:
                #     col_value = results.get(col_expr_label)

                if col_value is None:
                    columns.append({})
                else:
                    reconcile_rate = abs(results['suspense_balance']) / (abs(results['suspense_balance']) + abs(results['other_balance']))
                    move_name = move_name or results['name']
                    st_line_id = st_line_id or results['id']
                    col_class = ''
                    if col_expr_label == 'amount_currency':
                        col_value = results['amount_currency'] * reconcile_rate
                        col_class = 'number'
                        foreign_currency = self.env['res.currency'].browse(results['foreign_currency_id'])
                        formatted_value = report.format_value(col_value, currency=foreign_currency, figure_type=column['figure_type'])
                    elif col_expr_label == 'amount':
                        col_value *= reconcile_rate
                        col_class = 'number'
                        formatted_value = report.format_value(col_value, currency=report_currency, figure_type=column['figure_type'])
                        line_amounts[column['column_group_key']] += col_value
                        if col_value >= 0:
                            plus_totals[column['column_group_key']] += col_value
                        else:
                            less_totals[column['column_group_key']] += col_value
                    elif col_expr_label == 'date':
                        col_class = 'date'
                        formatted_value = format_date(self.env, col_value)
                    else:
                        formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                    columns.append({
                        'name': formatted_value,
                        'no_format': col_value,
                        'class': col_class,
                    })

            st_report_line = {
                'name': move_name,
                'columns': columns,
                'model': 'account.bank.statement.line',
                'caret_options': 'account.bank.statement',
                'level': 3,
            }

            # Only one of the values will be != 0, so the sum() will just return the not null value
            line_amount = sum(line_amounts.values())
            if line_amount > 0.0:
                st_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='plus_unreconciled_statement_lines'
                )
                plus_report_lines.append((0, st_report_line))
            else:
                st_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='less_unreconciled_statement_lines'
                )
                less_report_lines.append((0, st_report_line))
            st_report_line['id'] = report._get_generic_line_id(
                'account.bank.statement.line', st_line_id,
                parent_line_id=st_report_line['parent_id']
            )

            is_parent_unfolded = unfold_all or st_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                st_report_line['class'] = 'o_account_reports_filtered_lines'

        return (
            self._build_section_report_lines(report, options, journal, plus_report_lines, plus_totals,
                _("Including Unreconciled Bank Statement Receipts"),
                _("%s for Transactions(+) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
            self._build_section_report_lines(report, options, journal, less_report_lines, less_totals,
                _("Including Unreconciled Bank Statement Payments"),
                _("%s for Transactions(-) imported from your online bank account (dated today) that "
                  "are not yet reconciled in Odoo (Waiting the final reconciliation allowing finding the right "
                  "account)") % journal.suspense_account_id.display_name,
            ),
        )

    def _get_payment_report_lines(self, report, options, journal):
        ''' Retrieve the journal items used by the payment lines that are not yet reconciled and then, need to be
        displayed inside the report.
        :param options: The report options.
        :param journal: The journal as an account.journal record.
        :return:        The report lines for sections about statement lines.
        '''
        company_currency = journal.company_id.currency_id
        journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        accounts = journal._get_journal_inbound_outstanding_payment_accounts() \
                   + journal._get_journal_outbound_outstanding_payment_accounts()
        if not accounts:
            return [], []

        # Allow user managing payments without any statement lines.
        # In that case, the user manages transactions only using the register payment wizard.
        if journal.default_account_id in accounts:
            return [], []

        plus_report_lines = []
        less_report_lines = []
        plus_totals = {column['column_group_key']: 0.0 for column in options['columns']}
        less_totals = {column['column_group_key']: 0.0 for column in options['columns']}

        grouped_results = {}
        query, params = self._get_payment_query(report, options, accounts, journal)
        self._cr.execute(query, params)

        for results in self._cr.dictfetchall():
            grouped_results.setdefault(results['move_id'], {}).setdefault(results['column_group_key'], results)

        for column_group_results in grouped_results.values():

            columns = []
            line_amounts = {}
            move_name = None
            move_id = None
            account_id = None
            payment_id = None

            for column in options['columns']:
                col_expr_label = column['expression_label']
                results = column_group_results.get(column['column_group_key'], {})
                line_amounts[column['column_group_key']] = 0.0
                col_class = ''
                if col_expr_label == 'label':
                    col_value = results.get('ref')
                else:
                    col_value = results.get(col_expr_label)

                if col_expr_label == 'vendor_name':
                    col_value = self.env['account.move'].browse(results.get('move_id')).partner_id.name
                else:
                    col_value = results.get(col_expr_label)

                # columns.append({
                #     'no_format': col_value,
                #     'class': col_class,
                # })
                # print("col_valuecol_valuecol_value",col_value)

                # if col_value is None:
                #     print("wwwwwwwwwwwwwwwwwwwwwwwww",col_value)
                #     columns.append({})
                # else:
                #     print("col_expr_label------------------------",col_expr_label)
                move_name = move_name or results['name']
                move_id = move_id or results['move_id']
                account_id = account_id or results['account_id']
                payment_id = payment_id or results['payment_id']
                col_class = ''
                no_convert = journal_currency and results['currency_id'] == journal_currency.id
                if col_expr_label == 'amount_currency':
                    if no_convert:
                        foreign_currency = journal_currency
                        col_value = 0.0
                    else:
                        foreign_currency = self.env['res.currency'].browse(results['currency_id'])
                        col_value = results['amount_residual_currency'] if results['is_account_reconcile'] else results['amount_currency']
                    col_class = 'number'
                    formatted_value = report.format_value(col_value, currency=foreign_currency, figure_type=column['figure_type'])
                elif col_expr_label == 'amount':
                    if no_convert:
                        col_value = results['amount_residual_currency'] if results['is_account_reconcile'] else results['amount_currency']
                    else:
                        balance = results['amount'] if results['is_account_reconcile'] else results['balance']
                        col_value = company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to'])
                    col_class = 'number'
                    formatted_value = report.format_value(col_value, currency=journal_currency, figure_type=column['figure_type'])
                    line_amounts[column['column_group_key']] += col_value
                    if col_value >= 0:
                        plus_totals[column['column_group_key']] += col_value
                    else:
                        less_totals[column['column_group_key']] += col_value
                elif col_expr_label == 'date':
                    col_class = 'date'
                    formatted_value = format_date(self.env, col_value)
                elif col_expr_label == 'currency' and no_convert:
                    col_value = ''
                elif col_expr_label == 'payment_type':
                    col_value = self.env['account.payment'].browse(
                        results.get('payment_id')).payment_method_line_id.payment_method_id.name
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                elif col_expr_label == 'vendor_name':
                    col_value = self.env['account.move'].browse(results.get('move_id')).partner_id.name
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                else:
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                columns.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': col_class,
                })

            model = 'account.payment' if payment_id else 'account.move'
            pay_report_line = {
                'name': move_name,
                'columns': columns,
                'model': model,
                'caret_options': model,
                'level': 3,
            }

            if account_id in journal._get_journal_inbound_outstanding_payment_accounts().ids:
                pay_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='plus_unreconciled_payment_lines'
                )
                plus_report_lines.append((0, pay_report_line))
            else:
                pay_report_line['parent_id'] = report._get_generic_line_id(
                    None, None, markup='less_unreconciled_payment_lines'
                )
                less_report_lines.append((0, pay_report_line))
            pay_report_line['id'] = report._get_generic_line_id(
                model, payment_id or move_id,
                parent_line_id=pay_report_line['parent_id']
            )

            is_parent_unfolded = unfold_all or pay_report_line['parent_id'] in options['unfolded_lines']
            if not is_parent_unfolded:
                pay_report_line['class'] = 'o_account_reports_filtered_lines'

        return (
            self._build_section_report_lines(report, options, journal, plus_report_lines, plus_totals,
                _("(+) Outstanding Receipts"),
                _("Transactions(+) that were entered into Odoo, but not yet reconciled (Payments triggered by "
                  "invoices/refunds or manually)"),
            ),
            self._build_section_report_lines(report, options, journal, less_report_lines, less_totals,
                _("(-) Outstanding Payments"),
                _("Transactions(-) that were entered into Odoo, but not yet reconciled (Payments triggered by "
                  "bills/credit notes or manually)"),
            ),
        )



