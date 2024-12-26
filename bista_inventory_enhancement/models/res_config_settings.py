# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    adjustment_threshold = fields.Monetary(
        string="Adjustment Threshold",
        default=100)
    first_count_user_ids = fields.Many2many(
        'res.users', 'first_count_users_comp_rel', 'company_id', 'user_id',
        string='First Count Users')
    second_count_user_ids = fields.Many2many(
        'res.users', 'second_count_users_comp_rel', 'company_id', 'user_id',
        string='Second Count Users')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    adjustment_threshold = fields.Monetary(
        string="Adjustment Threshold", currency_field='company_currency_id',
        related='company_id.adjustment_threshold',
        default=100, readonly=False)
    first_count_user_ids = fields.Many2many(
        'res.users',
        related='company_id.first_count_user_ids',
        string='First Count Users', readonly=False)
    second_count_user_ids = fields.Many2many(
        'res.users',
        related='company_id.second_count_user_ids',
        string='Second Count Users', readonly=False)
