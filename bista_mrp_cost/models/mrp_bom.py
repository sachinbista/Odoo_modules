# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    mrp_labor_cost = fields.Float(string="Labor Cost/Per Unit")
    mrp_labor_account = fields.Many2one("account.account", string="Labor Account")
    mrp_overhead_cost = fields.Float(string="Overhead Cost/Per Unit")
    mrp_overhead_account = fields.Many2one("account.account", string="Overhead Account")
