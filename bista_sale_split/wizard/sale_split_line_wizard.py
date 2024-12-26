# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleSplitLineWizard(models.TransientModel):
    _name = 'sale.split.line.wizard'
    _description = "Sale Split Wizard"

    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        if self:
            for rec in self:
                rec.price_subtotal = rec.product_qty * rec.price_unit

    name = fields.Text(string='Description')
    wizard_id = fields.Many2one('sale.split.wizard')
    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float(string='Quantity', default=1)
    price_unit = fields.Float(string='Unit Price')
    product_uom = fields.Many2one('uom.uom', string='UOM')
    so_line_id = fields.Many2one('sale.order.line', string='Sale Line Id')
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_price_subtotal')

    @api.onchange('product_qty')
    def onchange_product_qty(self):
        sale_line_quantity = self.so_line_id.product_uom_qty
        if self.product_qty > sale_line_quantity:
            raise ValidationError("Cannot enter more quantity than original order quantity.")
