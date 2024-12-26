# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    manually_received_qty_uom = fields.Float(digits='Product Unit of Measure', copy=False, help="Qty that has been received for current line.")


    def _create_or_update_picking(self):
        if self.order_id.receipt_expectation == 'manual':
            return
        else:
            return super(PurchaseOrderLine, self)._create_or_update_picking()
