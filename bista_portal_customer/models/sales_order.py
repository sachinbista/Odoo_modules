from odoo import models, fields

class SalesOrder(models.Model):
    _inherit = 'sale.order'

    is_web_order = fields.Boolean("Web Order")
