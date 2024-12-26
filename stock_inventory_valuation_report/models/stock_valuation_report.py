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


class StockValuationReport(models.Model):
    _name = "stock.valuation.report"
    _description = "Stock Valuation Report"

    product_id = fields.Many2one('product.product')
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', string="Product Category")
    type_product = fields.Selection(related='product_id.type_product', string="Type")
                           
    item_type = fields.Selection(related='product_id.detailed_type')
    default_code = fields.Char(related='product_id.default_code',
                            string="Default Code")
    upc_code = fields.Char(related='product_id.barcode',
                            string="UPC Code")
    gtin = fields.Char(string="GTIN")
    on_hand = fields.Float(string="On Hand")
    open_po = fields.Float(string="Open PO")
    position = fields.Float(string="Position")
    open_so = fields.Float(string="Open SO")
    reserved_qty = fields.Float(string="Reserved Qty.")
    available_qty = fields.Float(string="Available Qty.")
    landed_cost_per_item = fields.Float(string="Landed Cost Per Item")
    starting_quantity = fields.Float(string="Starting Quantity")
    quantity_received = fields.Float(string="Quantity Received")
    quantity_shipped = fields.Float(string="Quantity Shipped")
    ending_quantity = fields.Float(string="Ending Quantity")
    starting_value = fields.Float(string="Starting Value")
    value_received = fields.Float(string="Value Received")
    valued_shipped = fields.Float(string="Value Shipped")
    ending_value = fields.Float(string="Ending Value")
    inv_adjustment_qty = fields.Float(string="Inv Adjustment")

class TypeProduct(models.Model):
    _name = "type.product"

    name = fields.Char(string="Name", required=True)
    color = fields.Integer(string='Color Index')
    type_product = fields.Selection([('inventory', "Inventory"),
                                     ('packaging', "Packaging"),  
                                     ('replacement_part', "Replacement Part"),
                                     ('other', "Other")], string="Type")

