# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import expression


class PurchaseReport(models.Model):
    _inherit = "purchase.report"



    trade_option = fields.Selection([('regular', 'Regular'), ('Trade In', 'Trade In/Up')], default="regular",
                                    string='Trade Option')


    def _select(self):
        return super(PurchaseReport, self)._select() + ", po.trade_option as trade_option"

    def _group_by(self):
        group_by_str = super(PurchaseReport, self)._group_by()
        group_by_str += ", po.trade_option"
        return group_by_str


    def _where(self):
        where_str = super(PurchaseReport, self)._where()
        where_str += " AND po.trade_option = 'Trade In'"
        return where_str