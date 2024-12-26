# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleProductPriceEntry(models.TransientModel):
    _name = 'sale.product.price.entry'
    _description = 'Sale Product Price Entry'

    product_template_id = fields.Many2one(
        'product.template', string="Product",
        required=True, domain=[('sale_ok', '=', True)])

    product_id = fields.Many2one(
        'product.product', string="Product",
        required=True, domain=[('sale_ok', '=', True)])
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    price_enrty = fields.Float('Price Entry', required=True, digits='Product Price', default=0.0)
