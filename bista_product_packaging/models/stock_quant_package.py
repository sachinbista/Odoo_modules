# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    sale_order_id = fields.Many2one('sale.order', string="Sale Order Ref")
    customer_id = fields.Many2one('res.partner', string="Customer")
    mo_id = fields.Many2one('mrp.production', string="Manufacture ID")
