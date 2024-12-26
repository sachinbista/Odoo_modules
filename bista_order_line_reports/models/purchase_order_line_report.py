# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models


class PurchaseOrderLineReport(models.Model):
    _name = "purchase.order.line.report"
    _description = "Sales Order Line Report"

    product_id = fields.Many2one('product.product')
    ordered_qty = fields.Float(string="Ordered Qty")
    delivered_qty = fields.Float(string="Received Qty")
    open_qty = fields.Float(string="Open Quantity")
    invoiced_qty = fields.Float(string="Billed Qty")
    unit_price = fields.Float(string="Unit Price")
    open_order_value = fields.Float(string="Open Order Value")
    subtotal = fields.Float(string="Subtotal")
    shipping_status = fields.Selection([("open", "Open"), ("done", "Done")], string="Shipping Status", )
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')



