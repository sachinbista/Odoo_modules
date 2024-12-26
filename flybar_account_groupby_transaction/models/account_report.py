# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _, osv


class AccountReport(models.Model):
    _inherit = "account.report"

    groupby_transaction_type = fields.Boolean(string="Transaction Type",
                                              compute=lambda x: x._compute_report_option_filter(
                                                  'groupby_transaction_type'),
                                              readonly=False, store=True, depends=['root_report_id'])

    def _init_options_transaction_type(self, options, previous_options=None):
        '''
        Initialize a filter based on the account_type of the line (trade/non trade, payable/receivable).
        Selects a name to display according to the selections.
        The group display name is selected according to the display name of the options selected.
        '''
        if not self.groupby_transaction_type:
            return

        options['transaction_type_ids'] = [
            # {'id': 'None', 'name': _("None"), 'selected': False},
            {'id': 'Transaction', 'name': _("Transaction"), 'selected': False},
        ]

        if previous_options and previous_options.get('transaction_type_ids'):
            previously_selected_ids = {x['id'] for x in previous_options['transaction_type_ids'] if x.get('selected')}
            for opt in options['transaction_type_ids']:
                opt['selected'] = opt['id'] in previously_selected_ids

        selected_options = {x['id']: x['name'] for x in options['transaction_type_ids'] if x['selected']}
        selected_ids = set(selected_options.keys())
        display_names = []

        def check_if_name_applicable(ids_to_match, string_if_match):
            '''
            If the ids selected are part of a possible grouping,
                - append the name of the grouping to display_names
                - Remove the concerned ids
            ids_to_match : the ids forming a group
            string_if_match : the group's name
            '''
            if len(selected_ids) == 0:
                return
            if ids_to_match.issubset(selected_ids):
                display_names.append(string_if_match)
                for selected_id in ids_to_match:
                    selected_ids.remove(selected_id)

        check_if_name_applicable({'None'}, _("None"))
        check_if_name_applicable({'Transaction'}, _("Transaction"))

        for sel in selected_ids:
            display_names.append(selected_options.get(sel))
        options['transaction_type_display_name'] = ', '.join(display_names)

