# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    auto_validate_transfer = fields.Boolean(string="Auto Validate Receipt", default=True, tracking=True)
    auto_validate_vendor_bill = fields.Boolean(string="Auto Validate Bill", default=False, tracking=True)
    bs_auto_validate_PO = fields.Boolean(string="Auto Validate PO", default=False, tracking=True,)
    bs_neg_prod_id = fields.Many2one("product.product", string="IC Allocation/Discount - Due-to/from", tracking=True)
