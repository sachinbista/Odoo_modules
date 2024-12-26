# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class Saleorder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection(
        selection_add=[
            ('proforma', 'PRO-FORMA')
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')