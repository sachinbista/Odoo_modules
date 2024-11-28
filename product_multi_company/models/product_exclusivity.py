from odoo import fields, models


class ProductExclusivity(models.Model):
    _name = "product.exclusivity"
    _description = "Product Exclusivity"

    name = fields.Char(string="Name", required=True)
