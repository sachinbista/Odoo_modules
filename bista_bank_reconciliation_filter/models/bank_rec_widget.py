# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _

class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    #Overwrite base method to remove default Customer/Vendor filter.
    #Added new default filter dynamically - Allow Bank Reconciliation.
    @api.depends('st_line_id')
    def _compute_amls_widget(self):
        for wizard in self:
            st_line = wizard.st_line_id

            context = {
                'search_view_ref': 'account_accountant.view_account_move_line_search_bank_rec_widget',
                'tree_view_ref': 'account_accountant.view_account_move_line_list_bank_rec_widget',
            }

            if wizard.partner_id:
                context['search_default_partner_id'] = wizard.partner_id.id

            dynamic_filters = []

            # == Dynamic Customer/Vendor filter ==
            journal = st_line.journal_id

            account_ids = set()

            inbound_accounts = journal._get_journal_inbound_outstanding_payment_accounts() - journal.default_account_id
            outbound_accounts = journal._get_journal_outbound_outstanding_payment_accounts() - journal.default_account_id

            # Matching on debit account.
            for account in inbound_accounts:
                account_ids.add(account.id)

            # Matching on credit account.
            for account in outbound_accounts:
                account_ids.add(account.id)

            rec_pay_matching_filter = {
                'name': 'receivable_payable_matching',
                'description': _("Customer/Vendor"),
                'domain': [
                    '|',
                    # Matching invoices.
                    '&',
                    ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                    ('payment_id', '=', False),
                    # Matching Payments.
                    '&',
                    ('account_id', 'in', tuple(account_ids)),
                    ('payment_id', '!=', False),
                ],
                'no_separator': True,
                'is_default': False,
            }
            #Added Dynamic filter Allow Bank Reconciliation
            allow_bank_reconciliation_filter = {
                'name': 'only_bank_reconciliation',
                'description': _("Allow Bank Reconciliation"),
                'domain': [
                    ('account_id.allow_bank_reconciliation', '=', True),
                    ('journal_id', '=', journal.id)
                ],
                'no_separator': False,
                'is_default': True,
            }
            misc_matching_filter = {
                'name': 'misc_matching',
                'description': _("Miscellaneous"),
                'domain': ['!'] + rec_pay_matching_filter['domain'],
                'is_default': False,
            }

            dynamic_filters.extend([rec_pay_matching_filter, misc_matching_filter, allow_bank_reconciliation_filter])
            # Stringify the domain.
            for dynamic_filter in dynamic_filters:
                dynamic_filter['domain'] = str(dynamic_filter['domain'])

            wizard.amls_widget = {
                'domain': st_line._get_default_amls_matching_domain(),

                'dynamic_filters': dynamic_filters,

                'context': context,
            }