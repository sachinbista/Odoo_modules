# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import json
import random

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import get_lang
from odoo.exceptions import UserError

from datetime import timedelta
from collections import defaultdict


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'
    _description = 'General Ledger Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        if 'transaction_type_ids' in options and options['transaction_type_ids'][0]['selected'] == True:
            lines = []
            date_from = fields.Date.from_string(options['date']['date_from'])
            company_currency = self.env.company.currency_id
            transaction_type = {}
            totals_by_column_group = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0})
            parent_line = {}
            for transaction in self._query_transaction_values(report, options):
                unfold_all = options.get('unfold_all')
                parent_line = {'id': '~transaction~' + str(int(random.randint(0, 10))),
                               'name': transaction[0].capitalize(),
                               'search_key': transaction[0],
                               'columns': [{'name': ''} for k in range(0, 6)],
                               'level': int(random.randint(0, 10)),
                               'unfoldable': False,
                               'unfolded': True,
                               'expand_function': '_report_expand_unfoldable_line_general_ledger_transaction',
                               'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
                               }
                lines.append(self._get_transaction_account_title_line(report, parent_line, options, False, False, {}))
                for account, column_group_results in self._query_account_values(report, options, transaction):
                    eval_dict = {}
                    has_lines = False
                    for column_group_key, results in column_group_results.items():
                        account_sum = results.get('sum', {})
                        account_un_earn = results.get('unaffected_earnings', {})
                        account_debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
                        account_credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
                        account_balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

                        eval_dict[column_group_key] = {
                            'amount_currency': account_sum.get('amount_currency', 0.0) + account_un_earn.get(
                                'amount_currency', 0.0),
                            'debit': account_debit,
                            'credit': account_credit,
                            'balance': account_balance,
                        }

                        max_date = account_sum.get('max_date')
                        has_lines = has_lines or (max_date and max_date >= date_from)

                        totals_by_column_group[column_group_key]['debit'] += account_debit
                        totals_by_column_group[column_group_key]['credit'] += account_credit
                        totals_by_column_group[column_group_key]['balance'] += account_balance

                    lines.append(self._get_transaction_account_title_line(report, False, options, account, has_lines, eval_dict))
            # Report total line.
            for totals in totals_by_column_group.values():
                totals['balance'] = company_currency.round(totals['balance'])

            # Tax Declaration lines.
            journal_options = report._get_options_journals(options)
            if len(options['column_groups']) == 1 and len(journal_options) == 1 and journal_options[0]['type'] in (
            'sale', 'purchase'):
                lines += self._tax_declaration_lines(report, options, journal_options[0]['type'])

            # Total line
            lines.append(self._get_total_line(report, options, totals_by_column_group))
            return [(0, line) for line in lines]
        return super()._dynamic_lines_generator(report=report,options=options,all_column_groups_expression_totals=all_column_groups_expression_totals)



    def _get_transaction_account_title_line(self, report,parent_line, options, account, has_lines, eval_dict):
        line_columns = []
        if parent_line:
            return parent_line
        else:
            for column in options['columns']:
                col_value = eval_dict[column['column_group_key']].get(column['expression_label'])
                col_expr_label = column['expression_label']

                if col_value is None or (col_expr_label == 'amount_currency' and not account.currency_id):
                    line_columns.append({})

                else:
                    if col_expr_label == 'amount_currency':
                        formatted_value = report.format_value(col_value, currency=account.currency_id, figure_type=column['figure_type'])
                    else:
                        formatted_value = report.format_value(col_value, figure_type=column['figure_type'], blank_if_zero=col_expr_label != 'balance')

                    line_columns.append({
                        'name': formatted_value,
                        'no_format': col_value,
                        'class': 'number',
                    })

            unfold_all = options.get('unfold_all')
            line_id = report._get_generic_line_id('account.account', account.id)
            is_in_unfolded_lines = any(
                report._get_res_id_from_line_id(line_id, 'account.account') == account.id
                for line_id in options.get('unfolded_lines')
            )
            return {
                'id': line_id,
                'name': f'{account.code} {account.name}',
                'search_key': account.code,
                'columns': line_columns,
                'level': 1,
                'unfoldable': has_lines,
                'unfolded': has_lines and (is_in_unfolded_lines or unfold_all),
                'expand_function': '_report_expand_unfoldable_line_general_ledger_transaction',
                'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            }





    def _query_transaction_values(self, report, options):
        """ Executes the queries, and performs all the computations.

        :return:    [(record, values_by_column_group), ...],  where
                    - record is an account.account record.
                    - values_by_column_group is a dict in the form {column_group_key: values, ...}
                        - column_group_key is a string identifying a column group, as in options['column_groups']
                        - values is a list of dictionaries, one per period containing:
                            - sum:                              {'debit': float, 'credit': float, 'balance': float}
                            - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                            - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
        """
        # Execute the queries and dispatch the results.
        query, params = self._get_query_transaction_sums(report, options)

        if not query:
            return []

        groupby_accounts = {}
        groupby_companies = {}
        groupby_transaction = {}
        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            column_group_key = res['column_group_key']
            key = res['key']
            if key == 'sum':
                groupby_accounts.setdefault(res['groupby'],
                                            {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_transaction.update({
                    res['transaction_type']: groupby_accounts
                })

            elif key == 'initial_balance':
                groupby_accounts.setdefault(res['groupby'],
                                            {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_transaction.update({
                    res['transaction_type']: groupby_accounts
                })
            elif key == 'unaffected_earnings':
                groupby_companies.setdefault(res['groupby'],
                                             {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_companies[res['groupby']][column_group_key] = res

        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # There is an unaffected earnings for each company but it's less costly to fetch all candidate accounts in
        # a single search and then iterate it.
        if groupby_transaction:
            transactions = list(groupby_transaction.keys())
        else:
            transactions = []

        # print("groupby_transaction::::::::",groupby_transaction)
        # b = [(transaction,account,groupby_transaction[transaction][account.id])for transaction in transactions for account in accounts]
        # return [(account, groupby_accounts[account.id]) for account in accounts]
        return [(transaction, groupby_transaction[transaction]) for transaction in transactions]




    def _query_account_values(self, report, options,transaction):
        """ Executes the queries, and performs all the computations.

        :return:    [(record, values_by_column_group), ...],  where
                    - record is an account.account record.
                    - values_by_column_group is a dict in the form {column_group_key: values, ...}
                        - column_group_key is a string identifying a column group, as in options['column_groups']
                        - values is a list of dictionaries, one per period containing:
                            - sum:                              {'debit': float, 'credit': float, 'balance': float}
                            - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                            - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
        """
        # Execute the queries and dispatch the results.
        query, params = self._get_query_transaction_sums(report, options)

        if not query:
            return []

        groupby_accounts = {}
        groupby_companies = {}
        groupby_transaction = {}
        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            column_group_key = res['column_group_key']
            key = res['key']
            if key == 'sum' and transaction[0] == res['transaction_type']:
                groupby_accounts.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res
            elif key == 'initial_balance' and transaction[0] == res['transaction_type']:
                groupby_accounts.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res
            elif key == 'unaffected_earnings' and transaction[0] == res['transaction_type']:
                groupby_companies.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_companies[res['groupby']][column_group_key] = res
        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # There is an unaffected earnings for each company but it's less costly to fetch all candidate accounts in
        # a single search and then iterate it.
        if groupby_companies:
            candidates_account_ids = self.env['account.account']._name_search(options.get('filter_search_bar'), [
                ('account_type', '=', 'equity_unaffected'),
                ('company_id', 'in', list(groupby_companies.keys())),
            ])
            for account in self.env['account.account'].browse(candidates_account_ids):
                company_unaffected_earnings = groupby_companies.get(account.company_id.id)
                if not company_unaffected_earnings:
                    continue
                for column_group_key in options['column_groups']:
                    unaffected_earnings = company_unaffected_earnings[column_group_key]
                    groupby_accounts.setdefault(account.id, {col_group_key: {} for col_group_key in options['column_groups']})
                    groupby_accounts[account.id][column_group_key]['unaffected_earnings'] = unaffected_earnings
                del groupby_companies[account.company_id.id]

        # Retrieve the accounts to browse.
        # groupby_accounts.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # - the unaffected earnings allocation.
        # Note a search is done instead of a browse to preserve the table ordering.
        if groupby_accounts:
            accounts = self.env['account.account'].search([('id', 'in', list(groupby_accounts.keys()))])
        else:
            accounts = []

        # print("transactions::::::::",transactions)
        # b = [(transaction,account,groupby_transaction[transaction][account.id])for transaction in transactions for account in accounts]
        # print("bbbbbbbb",b)
        # return [(account, groupby_accounts[account.id]) for account in accounts]
        return [(account, groupby_accounts[account.id]) for account in accounts]

    def _get_query_transaction_sums(self, report, options):
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
               - sums for all accounts.
               - sums for the initial balances.
               - sums for the unaffected earnings.
               - sums for the tax declaration.
               :return:                    (query, params)
               """
        options_by_column_group = report._split_options_per_column_group(options)
        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================
        for column_group_key, options_group in options_by_column_group.items():
            if not options.get('general_ledger_strict_range'):
                options_group = self._get_options_sum_balance(options_group)

            # Sum is computed including the initial balance of the accounts configured to do so, unless a special option key is used
            # (this is required for trial balance, which is based on general ledger)
            sum_date_scope = 'strict_range' if options_group.get('general_ledger_strict_range') else 'normal'

            query_domain = []

            if options.get('filter_search_bar'):
                query_domain.append(('account_id', 'ilike', options['filter_search_bar']))

            if options_group.get('include_current_year_in_unaff_earnings'):
                query_domain += [('account_id.include_initial_balance', '=', True)]

            tables, where_clause, where_params = report._query_get(options_group, sum_date_scope, domain=query_domain)
            params.append(column_group_key)
            params += where_params
            print("where_clause", where_clause)
            queries.append(f"""
                          SELECT
                              CASE 
                                  WHEN move.move_type = 'out_invoice' THEN 'sale'
                                  when move.move_type = 'out_refund' THEN 'credit_memo'
                                  WHEN move.move_type = 'in_invoice' THEN 'bill'
                                  WHEN move.move_type = 'in_refund' THEN 'bill_refund'
                                  WHEN move.move_type = 'entry' AND journal.type = 'bank' AND payment.partner_type = 'customer' THEN 'customer_payment_receipt'
                                  WHEN move.move_type = 'entry' AND journal.type = 'bank' AND payment.partner_type = 'supplier' THEN 'supplier_payment_receipt'
                                  WHEN move.move_type = 'entry' AND journal.type = 'general' AND journal.code ilike 'STJ' THEN 'misc'
                                  ELSE 'adjustments'
                              END AS transaction_type,
                              account_move_line.account_id                            AS groupby,
                              'sum'                                                   AS key,
                              MAX(account_move_line.date)                             AS max_date,
                              %s                                                      AS column_group_key,
                              COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                              SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                              SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                              SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                          FROM {tables}
                          LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                          LEFT JOIN account_journal journal  ON journal.id = account_move_line.journal_id
                          JOIN account_move move ON move.id = account_move_line.move_id
                          LEFT JOIN account_payment payment  ON payment.move_id = move.id
                          WHERE {where_clause}
                          GROUP BY account_move_line.account_id,transaction_type
                      """)

            # ============================================
            # 2) Get sums for the unaffected earnings.
            # ============================================
            if not options_group.get('general_ledger_strict_range'):
                unaff_earnings_domain = [('account_id.include_initial_balance', '=', False)]

                # The period domain is expressed as:
                # [
                #   ('date' <= fiscalyear['date_from'] - 1),
                #   ('account_id.include_initial_balance', '=', False),
                # ]

                new_options = self._get_options_unaffected_earnings(options_group)
                tables, where_clause, where_params = report._query_get(new_options, 'strict_range',
                                                                       domain=unaff_earnings_domain)
                params.append(column_group_key)
                params += where_params
                queries.append(f"""
                              SELECT
                                  CASE 
                                      WHEN move.move_type = 'out_invoice' THEN 'sale'
                                      when move.move_type = 'out_refund' THEN 'credit_memo'
                                      WHEN move.move_type = 'in_invoice' THEN 'bill'
                                      WHEN move.move_type = 'in_refund' THEN 'bill_refund'
                                      WHEN move.move_type = 'entry' AND journal.type = 'bank' AND payment.partner_type = 'customer' THEN 'customer_payment_receipt'
                                      WHEN move.move_type = 'entry' AND journal.type = 'bank' AND payment.partner_type = 'supplier' THEN 'supplier_payment_receipt'
                                      WHEN move.move_type = 'entry' AND journal.type = 'general' AND journal.code ilike 'STJ' THEN 'misc'
                                      ELSE 'adjustments'
                                  END AS transaction_type,
                                  account_move_line.company_id                            AS groupby,
                                  'unaffected_earnings'                                   AS key,
                                  NULL                                                    AS max_date,
                                  %s                                                      AS column_group_key,
                                  COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                                  SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                                  SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                                  SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                              FROM {tables}
                              LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                              LEFT JOIN account_journal journal  ON journal.id = account_move_line.journal_id
                              JOIN account_move move ON move.id = account_move_line.move_id
                              LEFT JOIN account_payment payment  ON payment.move_id = move.id
                              WHERE {where_clause}
                              GROUP BY account_move_line.company_id,transaction_type
                          """)

        return ' UNION ALL '.join(queries), params


    def _report_expand_unfoldable_line_general_ledger_transaction(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        print(">>>>>expandddd",line_dict_id)
        print(">>>>>options",options)
        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in  zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }

        report = self.env.ref('account_reports.general_ledger_report')
        if 'unfolded_lines' in options:
            model, model_id = report._get_model_info_from_id(options['unfolded_lines'][0])
            print(">>>unnnnmodelss",model,model_id)

        else:
            model, model_id = report._get_model_info_from_id(line_dict_id)

        if model != 'account.account':
            raise UserError(_("Wrong ID for general ledger line to expand: %s", line_dict_id))

        lines = []

        # Get initial balance
        if offset == 0:
            if unfold_all_batch_data:
                account, init_balance_by_col_group = unfold_all_batch_data['initial_balances'][model_id]
            else:
                account, init_balance_by_col_group = self._get_initial_balance_values(report, [model_id], options)[model_id]

            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, account.currency_id)

            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)

        # Get move lines
        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and not self._context.get('print_mode') else None
        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_results'][model_id]
            has_more = unfold_all_batch_data['has_more'].get(model_id, False)
        else:
            aml_results, has_more = self._get_aml_values(report, options, [model_id], offset=offset, limit=limit_to_load)
            aml_results = aml_results[model_id]

        next_progress = progress
        # for aml_result in aml_results.values():
        #     new_line = self._get_aml_line(report, line_dict_id, options, aml_result, next_progress)
        #     lines.append(new_line)
        #     next_progress = init_load_more_progress(new_line)

        return {
            'lines': lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': json.dumps(next_progress),
        }
