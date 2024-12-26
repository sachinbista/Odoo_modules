# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    tax_type_code = fields.Selection([
        ('GS', 'Goods and Services[GST]'), ('PG', 'State / Provincial Goods'), ('FT', 'Federal Excise'),
        ('SU', 'Sales and Use')],
        string="Tax Type Code")
