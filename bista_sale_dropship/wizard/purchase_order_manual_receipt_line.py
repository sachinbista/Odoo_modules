# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderManualReceiptLine(models.TransientModel):
    _inherit = 'purchase.order.manual.receipt.line'

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(PurchaseOrderManualReceiptLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.purchase_order_id.type_of_purchase == "dropship":
            sale_line_id = self.purchase_line_id.sudo().sale_line_id
            res.update({'sale_line_id': sale_line_id.id if sale_line_id else False})
        return res
