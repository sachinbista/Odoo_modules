# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'state')
    def _compute_qty_to_invoice(self):
        """
        @Overwrite
        """
        super(SaleOrderLine, self)._compute_qty_to_invoice()
        for line in self:
            if line.order_id.state in ['sale', 'done']:
                payment_term = line.order_id.payment_term_id
                if payment_term.force_all_products:
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    if line.product_id.invoice_policy == 'order':
                        line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                    else:
                        line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

