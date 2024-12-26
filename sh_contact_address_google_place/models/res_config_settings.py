# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_is_enable_google_api_key = fields.Boolean(
        related="company_id.sh_is_enable_google_api_key",
        string="Enable Google API",
        readonly=False)

    sh_google_api_key = fields.Char(
        related="company_id.sh_google_api_key",
        string="Key",
        readonly=False)

    sh_restricted_country_ids = fields.Many2many(
        string='Restricted Countries',
        related='company_id.sh_restricted_country_ids',
    )
    

class ResCompany(models.Model):
    _inherit = "res.company"

    sh_is_enable_google_api_key = fields.Boolean(
        string="Enable Google API")

    sh_google_api_key = fields.Char(
        string="Key")
    
    
    sh_restricted_country_ids = fields.Many2many(
        string='Restricted Countries',
        comodel_name='res.country',
    )
    
