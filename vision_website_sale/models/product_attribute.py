from odoo import models, fields, api


class Attribute(models.Model):
    _inherit = 'product.attribute'

    attribute_type = fields.Selection([
        ('color', 'Color'),
        ('size', 'Size')
    ], string='Attribute Type')

