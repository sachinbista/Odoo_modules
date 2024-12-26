# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, api, fields, _
from datetime import datetime
from odoo.tools.misc import formatLang



class Partner(models.Model):
    _inherit = 'res.partner'

    transactions_count = fields.Integer(string='History', compute='_compute_transactions_count')

    company_type = fields.Selection(string='Company Type',
                                    selection=[('person', 'Individual'), ('company', 'Company')],
                                    compute='_compute_company_type', inverse='_write_company_type', default='person')

    is_company = fields.Boolean(string='Is a Company', default=False,
                                help="Check if the contact is a company, otherwise it is a person")

    gender_partner = fields.Selection(selection=[('Male', 'Male'), ('Female', 'Female')], string='Partner Gender',
                                      default='Male')
    birth_year_selection = fields.Selection(selection=lambda self: self.year_dynamic_selection(), string='Birth Year')
    ann_year_selection = fields.Selection(selection=lambda self: self.year_dynamic_selection(),
                                          string='Anniversary Year')
    propose_year_selection = fields.Selection(selection=lambda self: self.year_dynamic_selection(),
                                              string='Proposal Year')
    short_name = fields.Char(string='Vendor Short Name')
    phonecall_count = fields.Integer(string='Phone Calls', compute='_compute_phonecalls_count')

    total_debit_bill_count = fields.Char(string='Vendor Bills', compute='get_payable_bill_count')

    def get_payable_bill_count(self):
        for res in self:
            res.total_debit_bill_count = self.format_value(res.debit, res.currency_id)

    def format_value(self, amount, currency=False, blank_if_zero=False):
        currency_id = currency or self.env.company.currency_id
        if currency_id.is_zero(amount):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            amount = abs(amount)

        if self.env.context.get('no_format'):
            return amount
        return formatLang(self.env, amount, currency_obj=currency_id)

    def _compute_phonecalls_count(self):
        for phonecall in self:
            phonecall_count = self.env['voip.phonecall'].search_count([('partner_id', '=', phonecall.id)])
            phonecall.phonecall_count = phonecall_count


    def year_dynamic_selection(self):
        select = [(str(num), str(num)) for num in range(1900, (datetime.now().year) + 1)]
        return select

    def _compute_transactions_count(self):
        for transactions in self:
            transactions_count = self.env['client.history'].search_count([('partner_id', '=', transactions.id)])
            transactions.transactions_count = transactions_count

    def action_view_history_list(self):
        self.ensure_one()
        action = self.env.ref('darakjian_client_history.action_client_history')

        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': 'form',
            'view_mode': action.view_mode,
            'target': action.target,
            'context': "{}",
            'res_model': action.res_model,
            'domain': [('partner_id', '=', self.id)],
        }

    def action_view_reach_out_list_button(self):
        self.ensure_one()
        action = self.env.ref('crm_darakjian_customizations.action_view_reach_out_list')

        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': "{}",
            'res_model': action.res_model,
            'domain': [('partner', '=', self.id)],
        }


class ResUsers(models.Model):
    _inherit = 'res.users'

    website_published = fields.Boolean(string='Publish On Website')


    # @api.multi
    def team_publish_button(self):
        self.ensure_one()
        return self.write({'website_published': not self.website_published})