from odoo import fields, models, api, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_group_id = fields.Many2one('product.group', string='Product Group')
    product_group_id_cartons = fields.Many2one('product.group.carton', string='Product Group - Cartons')
    product_sub_categ_1 = fields.Many2one('product.sub.category.a', string='Product Sub-Category 1')
    product_sub_categ_2 = fields.Many2one('product.sub.category.b', string='Product Sub-Category 2')
    categ_id = fields.Many2one('product.category', string='Product Category')


    @api.onchange('product_id')
    def onchange_product(self):
        for rec in self:
            rec.product_group_id = rec.product_id.product_group_id
            rec.product_group_id_cartons = rec.product_id.product_group_id_cartons
            rec.product_sub_categ_1 = rec.product_id.product_sub_categ_1
            rec.product_sub_categ_2 = rec.product_id.product_sub_categ_2
            rec.categ_id = rec.product_id.categ_id
