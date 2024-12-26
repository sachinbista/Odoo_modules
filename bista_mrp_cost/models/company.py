# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    mrp_labor_cost = fields.Float(string="Labor Cost")
    mrp_labor_account = fields.Many2one("account.account", string="Labor Account")
    mrp_overhead_cost = fields.Float(string="Overhead Cost")
    mrp_overhead_account = fields.Many2one("account.account", string="Overhead Account")
