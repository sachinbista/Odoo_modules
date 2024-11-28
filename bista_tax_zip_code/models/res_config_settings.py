# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    set_tax_account_zip_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        domain=[('deprecated', '=', False)],
        string="Default Tax for Zip Code Account",
        default_model="account.account",
        help="Account that will be set on Tax for Zip Code Account by default.")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    set_tax_account_zip_id = fields.Many2one(
        comodel_name='account.account',
        string="Default Tax for Zip Code Account",
        readonly=False,
        check_company=True,
        default_model="account.account",
        related='company_id.set_tax_account_zip_id',
        domain=[('deprecated', '=', False)])


