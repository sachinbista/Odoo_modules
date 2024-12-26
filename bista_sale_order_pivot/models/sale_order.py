from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale order inherit'

    customer_po = fields.Char(string="Customer PO")
