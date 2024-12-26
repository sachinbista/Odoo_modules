# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = "Update Sale Order Warehouse"

    ship_from_warehouse = fields.Boolean("Ship From Warehouse", default=False)
