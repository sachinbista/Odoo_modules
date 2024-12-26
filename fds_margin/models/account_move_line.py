# -*- coding: utf-8 -*-

from odoo import models, fields, api, _



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    margin = fields.Float(
        "Margin", compute='_compute_margin',
        digits='Product Price', store=True, groups="base.group_user", precompute=True)
    margin_percent = fields.Float(
        "Margin (%)", compute='_compute_margin', store=True, groups="base.group_user", precompute=True)
    purchase_price = fields.Float(
        string="Cost", compute="_compute_purchase_price",
        digits='Product Price', store=True, readonly=False, copy=False, precompute=True,
        groups="base.group_user")

    @api.depends('price_subtotal', 'quantity', 'purchase_price')
    def _compute_margin(self):
        for line in self.filtered(lambda a: not a.product_id.exclude_margin):
            line.margin = line.price_subtotal - (line.purchase_price * line.quantity)
            line.margin_percent = line.price_subtotal and line.margin / line.price_subtotal

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom_id')
    def _compute_purchase_price(self):
        for line in self.filtered(lambda a: not a.product_id.exclude_margin):
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)
            product_cost = line.product_id.standard_price
            # line.purchase_price = line._convert_price(product_cost, line.product_id.uom_id)
            line.purchase_price = product_cost
