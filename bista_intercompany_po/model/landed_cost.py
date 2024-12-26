from odoo import models, api, fields, _

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    internal_order_ref = fields.Char(string="Order Reference/Owner's reference")