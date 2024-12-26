# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_package = fields.Boolean(string="Reusable Package")
