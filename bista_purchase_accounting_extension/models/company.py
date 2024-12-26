# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"


    good_shipped_acc_id = fields.Many2one(comodel_name = "account.account",
                                          string="Goods Shipped Account")
