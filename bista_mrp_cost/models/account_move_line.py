# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    analytic_account_id = fields.Many2one('account.analytic.account')

    @api.model_create_multi
    def create(self, vals):
        ret = super(AccountMoveLine, self).create(vals)
        stock_move = ret.move_id.stock_move_id
        if stock_move:
            production = stock_move.production_id or stock_move.raw_material_production_id
            if production and production.analytic_account_id:
                ret.analytic_account_id = production.analytic_account_id
        return ret
