# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    consignment_stock_move = fields.Boolean(
        config_parameter="bista_consignment_report.consignment_stock_move",
        string='Stock Move',
        readonly=False)
    consignment_account_id = fields.Many2one('account.account',config_parameter="bista_consignment_report.consignment_account_id", string="Consignment Account")
