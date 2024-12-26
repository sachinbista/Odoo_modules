
from odoo import fields, models


class ProductSize(models.Model):
    _name = "product.template.retailer"
    _description = "Product template retailer"

    name = fields.Char(string="Name", required=True)
