# -*- coding: utf-8 -*-

from odoo import models, _, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def write(self, vals):
        if 'standard_price' in vals:
            for rec in self:
                qry1 = """DELETE FROM ir_property WHERE name = 'standard_price' 
                AND res_id = 'product.product,%s' """ % rec.id
                rec.sudo()._cr.execute(qry1)
        res = super(ProductProduct, self).write(vals)
        return res


class IrProperty(models.Model):
    _inherit = 'ir.property'

    @api.constrains('value_float')
    def _change_company(self):
        for rec in self:
            if rec.name == 'standard_price' and rec.fields_id.model == 'product.product':
                rec.update({'company_id': False})
