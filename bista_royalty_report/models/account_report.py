# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api


class AccountReport(models.Model):
    _inherit = "account.report"

    filter_royalty_agent = fields.Boolean(string="Royalty Agent",
                                          compute=lambda x: x._compute_report_option_filter('filter_royalty_agent'),
                                          readonly=False, store=True, depends=['root_report_id'])

    def _init_options_royalty_agents(self, options, previous_options=None):
        if not self.filter_royalty_agent:
            return
        options['royalty_agent'] = True
        options['royalty_agents_ids'] = previous_options and previous_options.get('royalty_agents_ids') or []
        selected_royalty_agents_ids = [int(royalty_agents) for royalty_agents in options['royalty_agents_ids']]
        selected_royalty_agents = (selected_royalty_agents_ids and self.env['res.partner'].browse(
            selected_royalty_agents_ids) or self.env['res.partner'])
        options['selected_royalty_agents_ids'] = selected_royalty_agents.mapped('name')

    @api.model
    def _get_options_royalty_agents_domain(self, options):
        domain = []
        if options.get('royalty_agents_ids'):
            royalty_agent_ids = [int(royalty_agents) for royalty_agents in options['royalty_agents_ids']]
            domain.append(('royalty_agents_ids', 'in', royalty_agent_ids))
        return domain

    def _get_options_domain(self, options, date_scope):
        domain = super(AccountReport, self)._get_options_domain(options, date_scope)
        domain += self._get_options_royalty_agents_domain(options)
        return domain
