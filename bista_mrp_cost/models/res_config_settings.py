# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_labor_cost = fields.Float(related="company_id.mrp_labor_cost", readonly=False)
    mrp_labor_account = fields.Many2one("account.account", related="company_id.mrp_labor_account", readonly=False)
    mrp_overhead_cost = fields.Float(related="company_id.mrp_overhead_cost", readonly=False)
    mrp_overhead_account = fields.Many2one("account.account", related="company_id.mrp_overhead_account", readonly=False)
