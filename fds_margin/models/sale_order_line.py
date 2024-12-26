# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom')
    def _compute_purchase_price(self):
        for line in self.filtered(lambda a: not a.product_id.exclude_margin):
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)
            product_cost = line.product_id.standard_price
            line.purchase_price = line._convert_price(product_cost, line.product_id.uom_id)

    @api.depends('price_subtotal', 'product_uom_qty', 'purchase_price')
    def _compute_margin(self):
        for line in self.filtered(lambda a: not a.product_id.exclude_margin):
            line.margin = line.price_subtotal - (line.purchase_price * line.product_uom_qty)
            line.margin_percent = line.price_subtotal and line.margin / line.price_subtotal
