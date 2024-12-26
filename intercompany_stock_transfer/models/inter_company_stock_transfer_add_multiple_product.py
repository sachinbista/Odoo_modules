# -*- coding: utf-8 -*-

from odoo import fields, models


class AddMultipleProduct(models.TransientModel):
    _name = 'resupply.add.multiple.product'
    _description = 'Resupply Add Multiple Product'

    product_ids = fields.Many2many('product.product', string="Product")

    def add_multipl_product(self):
        resupply_line = self.env['inter.company.stock.transfer.line']
        for line in self.product_ids:
            product = self.env['product.product'].browse([line.id])
            resupply_line.create({
                'name': product.display_name,
                'stock_transfer_id': self._context.get('active_id'),
                'product_id': line.id,
                'product_uom': product.uom_id.id,
            })
        return
