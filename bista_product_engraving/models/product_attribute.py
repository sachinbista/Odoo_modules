from odoo import models, fields


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_engrave = fields.Boolean(string='For Engraving?')
    engrave_style = fields.Selection(
        [('engrave_text', 'Engrave Text'), ('engrave_font', 'Engrave Font')],
        default='engrave_text'
    )