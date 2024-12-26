# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression


class StockProductionLot(models.Model):
    _inherit = 'stock.lot'

    product_barcode = fields.Char(related="product_id.barcode", store=True)
    location_id = fields.Many2one('stock.location')
    tracking = fields.Selection(related="product_id.tracking", store=True)

    @api.model
    def _get_fields_stock_barcode(self):
        ret = super(StockProductionLot, self)._get_fields_stock_barcode()
        ret += ['location_id', 'product_qty']
        return ret
