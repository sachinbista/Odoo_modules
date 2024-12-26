# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    @api.model_create_multi
    def create(self, values_list):
        messages = []
        check_duplicates = []
        for vals in values_list:
            picking_ids = [p[1] for p in vals.get('picking_ids', []) if p]
            picking_ids = self.env['stock.picking'].browse(picking_ids)
            for picking in picking_ids:
                sales = picking.move_ids_without_package.sale_line_id.order_id.filtered(
                    lambda sale: sale.payment_term_id.allow_delivery_validate_without_full_payment)
                for sale_order in sales:
                    invoice_ids = sale_order.invoice_ids
                    total_amount = sale_order.amount_total
                    if invoice_ids and sum(invoice_ids.mapped('amount_total_signed')) == total_amount:
                        balance_due = sum(invoice_ids.mapped('amount_residual'))
                        if balance_due != 0 and picking.name not in check_duplicates:
                            messages.append(_('Transfer %s has Sales order %s with $ %.2f payment due.') %
                                            (picking.name, sale_order.name, balance_due))
                            check_duplicates.append(picking.name)
                    elif picking.name not in check_duplicates:
                        messages.append(_("All products are not invoiced for "
                                          "Sales order '%s' with delivery '%s'.") %
                                        (sale_order.name, picking.name))
                        check_duplicates.append(picking.name)

        if messages:
            error_message = "User is not allowed to validate the delivery orders.\n"
            error_message += "\n".join(messages)
            raise ValidationError(error_message)

        return super(StockPickingBatch, self).create(values_list)


    def write(self, values):
        result = super(StockPickingBatch, self).write(values)
        for each in self:
            message = []
            check_duplicate = []
            for picking in each.picking_ids:
                sale = picking.move_ids_without_package.sale_line_id.order_id
                if sale:
                    for sale_order in sale:
                        if sale_order.payment_term_id.allow_delivery_validate_without_full_payment:
                            invoice_ids = sale.invoice_ids
                            if invoice_ids and sum(
                                    invoice_ids.mapped('amount_total_signed')) == sale_order.amount_total:
                                balance_due = sum(invoice_ids.mapped('amount_residual'))
                                if balance_due != 0 and picking.name not in check_duplicate:
                                    message.append(
                                        _('Transfer %s has Sales order %s with $ %.2f payment due.')
                                        % (picking.name, sale_order.name, balance_due))
                                    check_duplicate.append(picking.name)
                            else:
                                if picking.name not in check_duplicate:
                                    message.append(
                                        _('All products are not invoiced for Sales order %s.') % (sale_order.name))
                                    check_duplicate.append(picking.name)
            if message:
                error_message = "User is not allowed to validate the delivery orders.\n"
                error_message += "\n".join(message)
                raise ValidationError(error_message)
        return result
