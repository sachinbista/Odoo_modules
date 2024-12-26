# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    # added to set goglow store id from sale order to invoice. To count amazon charges.
    def _create_invoices(self, sale_order):
        self.ensure_one()
        sale_order.ensure_one()
        result = super(SaleAdvancePaymentInv, self)._create_invoices(sale_order)
        for invoice in result:
            if sale_order.goflow_store_id:
                invoice.update({'goflow_store_id': sale_order.goflow_store_id.id})
        return result
