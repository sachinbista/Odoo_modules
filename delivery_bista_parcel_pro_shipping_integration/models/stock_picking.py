# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, Command, _


class StockPicking(models.Model):
    _inherit = "stock.picking"



    service_description = fields.Char(string="Service",readonly=True)
    shipping_cost = fields.Float(string="Shipping Cost",readonly=True)