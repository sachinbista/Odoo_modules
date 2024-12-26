from odoo import fields, models


class ProductSize(models.Model):
    _name = "product.size"
    _description = "Product Size"

    name = fields.Char(string="Name", required=True)
