from odoo import fields, models


class ProductSubCategory(models.Model):
    _name = "product.sub.category.a"
    _description = "Product Sub Category"

    name = fields.Char(string="Name", required=True)


class ProductSubCategoryB(models.Model):
    _name = "product.sub.category.b"
    _description = "Product Sub Category B"

    name = fields.Char(string="Name", required=True)
