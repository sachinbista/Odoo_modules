# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _

class StockMove(models.Model):
    _inherit = "stock.move"

    is_special = fields.Boolean(string="Is Special", copy=False)