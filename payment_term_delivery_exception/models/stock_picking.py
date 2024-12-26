# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        if not self._context.get('shopify_picking_validate'):
            for picking in self.filtered(lambda p: p.sale_id and p.picking_type_code == 'outgoing'):
                sale_order = picking.sale_id
                if sale_order.payment_term_id.allow_delivery_validate_without_full_payment:
                    invoice_ids = sale_order.invoice_ids
                    if invoice_ids and sum(invoice_ids.mapped('amount_total_signed')) == sale_order.amount_total:
                        balance_due = sum(invoice_ids.mapped('amount_residual'))
                        if balance_due != 0:
                            raise ValidationError(_('User is not allowed to validate the delivery order.\nSales order %s has $ %s payment due.')
                                                  % (sale_order.name, balance_due))
                    elif (sum(invoice_ids.mapped('amount_total_signed')) <
                           sale_order.amount_total):
                        raise ValidationError(_('All products are not Invoiced for Sale Order %s .') % sale_order.name)
        return super(StockPicking, self).button_validate()
