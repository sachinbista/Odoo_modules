from odoo import fields, models


class ProductCollection(models.Model):
    _name = "product.collection"
    _description = "Product Collection"

    name = fields.Char(string="Name", required=True)
