# -*- coding: utf-8 -*-
from odoo import models, api,fields

class Company(models.Model):
    _inherit = 'res.company'

    pos_report_notify_user_ids = fields.Many2many(string="Pos Report Notify User", comodel_name='res.users')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_report_notify_user_ids = fields.Many2many(related="company_id.pos_report_notify_user_ids",string="Pos Report Notify User", comodel_name='res.users',readonly=False)