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

    filter_user = fields.Boolean(string="Users",
                                 compute=lambda x: x._compute_report_option_filter('filter_user'),
                                 readonly=False, store=True, depends=['root_report_id'])

    filter_category = fields.Boolean(string="Category",
                                     compute=lambda x: x._compute_report_option_filter('filter_category'),
                                     readonly=False, store=True, depends=['root_report_id'])

    def _init_options_users(self, options, previous_options=None):
        if not self.filter_user:
            return
        options['user'] = True
        options['users_ids'] = previous_options and previous_options.get('users_ids') or []
        selected_users_ids = [int(users) for users in options['users_ids']]
        selected_users = (
                selected_users_ids and self.env['res.users'].browse(selected_users_ids) or self.env['res.users'])
        options['selected_users_ids'] = selected_users.mapped('name')

    @api.model
    def _get_options_users_domain(self, options):
        domain = []
        if options.get('users_ids'):
            user_ids = [int(users) for users in options['users_ids']]
            domain.append(('users_ids', 'in', user_ids))
        return domain

    @api.model
    def _init_options_category(self, options, previous_options=None):
        if not self.filter_category:
            return
        options['category'] = True
        options['category_ids'] = previous_options and previous_options.get('category_ids') or []
        selected_category_ids = [int(category) for category in options['category_ids']]
        selected_categories = (
                selected_category_ids and self.env['product.category'].browse(selected_category_ids) or self.env[
            'product.category'])
        options['selected_category_ids'] = selected_categories.mapped('name')

    @api.model
    def _get_options_category_domain(self, options):
        domain = []
        if options.get('category_ids'):
            category_ids = [int(category) for category in options['category_ids']]
            domain.append(('category_ids', 'in', category_ids))
        return domain

    def _get_options_domain(self, options, date_scope):
        domain = super(AccountReport, self)._get_options_domain(options, date_scope)
        domain += self._get_options_users_domain(options)
        domain += self._get_options_category_domain(options)
        return domain
