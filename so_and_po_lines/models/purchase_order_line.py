from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'


    date_orderd = fields.Datetime(related='order_id.date_order', string="Order Date",copy=False, store=True)
    brand = fields.Many2one(related='product_id.brand', string="Brand",copy=False, store=True)
    manufacturer = fields.Many2one(related='product_id.manufacturer', string="Manufacturer", copy=False, store=True)
