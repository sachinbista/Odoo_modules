from odoo import fields, models


class ProductRegionAvailability(models.Model):
    _name = "product.region.availability"
    _description = "Product Region Availability"

    name = fields.Char(string="Name", required=True)
