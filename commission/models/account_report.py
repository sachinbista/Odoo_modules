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

    filter_agent = fields.Boolean(string="Commission Agent",
                                  compute=lambda x: x._compute_report_option_filter('filter_agent'),
                                  readonly=False, store=True, depends=['root_report_id'])

    def _init_options_agents(self, options, previous_options=None):
        if not self.filter_agent:
            return
        options['agent'] = True
        options['agents_ids'] = previous_options and previous_options.get('agents_ids') or []
        selected_agents_ids = [int(agents) for agents in options['agents_ids']]
        selected_agents = (
                selected_agents_ids and self.env['res.partner'].browse(selected_agents_ids) or self.env['res.partner'])
        options['selected_agents_ids'] = selected_agents.mapped('name')


    @api.model
    def _get_options_agents_domain(self, options):
        domain = []
        if options.get('agents_ids'):
            agent_ids = [int(agents) for agents in options['agents_ids']]
            domain.append(('agents_ids', 'in', agent_ids))
            # domain.append(('agent', '=', True))
        return domain

    def _get_options_domain(self, options, date_scope):
        domain = super(AccountReport, self)._get_options_domain(options, date_scope)
        domain += self._get_options_agents_domain(options)
        return domain
