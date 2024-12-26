# -*- coding: utf-8 -*-
from odoo import models, api, fields


class BoxAndPallet(models.Model):

    _name = "fds.box_and_pallet"
    _description = "Boxs & Pallets"

    _sql_constraints = [('name_uniq', 'unique (name)', 'Product already in use.')]
    name = fields.Char(compute="comp_name", store=True)    
    product = fields.Many2one('product.template', string="Product", required=True, store=True)
    box_pallet = fields.Integer(string="Per Box/Pallet", required=True, store=True)

    @api.depends('product')
    def comp_name(self):
        for record in self:
            record.name = record.product.default_code

    def get_box_pallet_by_product_template_list(self, product_tmp_ids):
        return {
            bp.product.id: bp.box_pallet
            for bp in self.search([('product', 'in', product_tmp_ids)])
        }

    def compute_box_pallet_loose(self, box_pallet_qty, product_qty):
        return product_qty // box_pallet_qty, product_qty % box_pallet_qty
