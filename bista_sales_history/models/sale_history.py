# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class SaleHistoryStore(models.Model):
    _name = "sale.history.store"
    _description = 'Sales History Store'



    customer_id = fields.Char(string='Customer', copy=False)
    customer_reference = fields.Char(string="Customer Order #", copy=False)
    warehouse_name = fields.Char(string="Warehouse", copy=False)
    orders = fields.Float(string="Orders", copy=False, store=True)
    units_sold = fields.Float(string="Units Sold", copy=False, store=True)
    commission_fee = fields.Float(string="Commissions & Fees", copy=False, store=True)
    avg_order_value = fields.Float(string="Avg. Order Value", copy=False, store=True)
    products_sold = fields.Float(string="Products Sold", copy=False, store=True)
    skus_sold = fields.Float(string="SKU's Sold", copy=False, store=True)
    cost_of_goods_sold = fields.Float(string="Cost of Goods Sold", copy=False, store=True)
    shipping_cost = fields.Float(string="Shipping Cost", copy=False, store=True)
    gross_revenue = fields.Float(string="Gross Revenue", copy=False, store=True)



class SaleHistoryProduct(models.Model):
    _name = "sale.history.product"
    _description = "Sale History Product"

    type = fields.Char('Type', copy=False)
    date_order = fields.Date(string='Date',copy=False,store=True)
    number = fields.Char(string='Number', copy=False)
    product_name = fields.Char('Product', copy=False)
    product_brand = fields.Char(string='Brand', copy=False)
    description = fields.Char(string='Description', copy=False)
    item_number = fields.Char(string='Item number', copy=False)
    reference = fields.Char(string="PO.#", copy=False)
    customer_id = fields.Char(string='Customer', copy=False)
    qty = fields.Float(string="Quantity", copy=False, store=True)
    sale_price = fields.Float(string="Sale Price", copy=False, store=True)
    amount = fields.Float(string="Amount", copy=False, store=True)
    orders = fields.Float(string="Orders", copy=False, store=True)
    units_sold = fields.Float(string="Units Sold", copy=False, store=True)
    commission_fee = fields.Float(string="Commissions & Fees", copy=False, store=True)
    avg_price_per_item = fields.Float(string="Avg. Price Per Item", copy=False, store=True)
    products_sold = fields.Float(string="Products Sold", copy=False, store=True)
    skus_sold = fields.Float(string="SKU's Sold", copy=False, store=True)
    cost_of_goods_sold =fields.Float(string="Cost of Goods Sold", copy=False, store=True)
    shipping_cost = fields.Float(string="Shipping Cost", copy=False, store=True)
    gross_revenue = fields.Float(string="Gross Revenue", copy=False, store=True)

