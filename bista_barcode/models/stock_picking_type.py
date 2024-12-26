# -*- coding: utf-8 -*-


from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    scan_full_lot = fields.Boolean(default=True)
    scan_full_qty = fields.Boolean(default=True)
    scan_package = fields.Boolean(default=True)
    allow_edit = fields.Boolean(default=True)

    decrement_btn = fields.Boolean()
    increment_btn = fields.Boolean()

    def _get_fields_stock_barcode(self):
        ret = super(StockPickingType, self)._get_fields_stock_barcode()
        ret += ['scan_full_lot', 'scan_full_qty',
                'is_package', 'decrement_btn',
                'increment_btn', 'scan_package', 'allow_edit']
        return ret
