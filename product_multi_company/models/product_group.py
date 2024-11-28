from odoo import fields, models


class ProductGroup(models.Model):
    _name = "product.group"
    _description = "Product Group"

    name = fields.Char(string="Name", required=True)

class ProductGroupCarton(models.Model):
    _name = "product.group.carton"
    _description = "Product Group - Cartons"

    name = fields.Char(string="Name", required=True)