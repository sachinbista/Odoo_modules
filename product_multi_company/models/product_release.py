from odoo import fields, models


class ProductRelease(models.Model):
    _name = "product.release"
    _description = "Product Release"

    name = fields.Char(string="Name", required=True)
