# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    s_exclude_from_inventory_report = fields.Boolean(string="Exclude From Inventory Report",
                                                     default=False,
                                                     help="mark boolean true to exclude this location from the inventory report")

    s_is_subcontract_location = fields.Boolean(string="Subcontract Location")
