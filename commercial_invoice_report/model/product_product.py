from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ppi_CountryOfOrigin = fields.Many2one('res.country', string='Country of Origin')
    quantity_svl = fields.Float(string="Quantity")