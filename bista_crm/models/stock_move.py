# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_src_account(self, accounts_data):
        res =super(StockMove , self)._get_src_account(accounts_data=accounts_data)
        if self.purchase_line_id and \
        self.purchase_line_id.order_id and self.purchase_line_id.order_id.trade_option !='regular':
            trade_account = self.env['ir.config_parameter'].get_param('bista_crm.trade_account_id')
            if trade_account:
                return trade_account
        return res