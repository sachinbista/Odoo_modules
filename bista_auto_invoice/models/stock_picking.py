# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Picking(models.Model):
    _inherit = 'stock.picking'

    invoice_warning = fields.Char(compute='_compute_invoice_warning', store=True)
    account_move_ids = fields.Many2many('account.move',
                                        relation="stock_picking_id_account_move_id_ref",
                                        column1="stock_picking_id",
                                        column2="account_move_id")

    @api.depends("move_ids.invoiced")
    def _compute_invoice_warning(self):
        for picking in self:
            warning = False
            # picking.account_move_ids.order_id = picking.sale_id
            if picking.picking_type_id.code == 'outgoing':
                not_invoiced = any(line.sale_line_id and not line.invoiced for line in picking.move_ids)
                if not_invoiced:
                    warning = "Caution!: Some products are not invoiced yet."
            picking.invoice_warning = warning

    def button_validate(self):
        ret = super().button_validate()
        self._generate_invoice()
        return ret

    def _generate_invoice(self):
        for picking in self:
            if picking.state == 'done' and self.sale_id.payment_term_id.auto_invoice and picking.carrier_id or picking.carrier_tracking_ref:
                line_ids = picking.move_ids.mapped('sale_line_id')
                sale_orders = line_ids.mapped("order_id")
                account_moves = sale_orders._generate_invoice(picking)
                if account_moves:
                # if self.sale_id.payment_term_id.auto_payment:
                #     account_moves.with_context(auto_inv_payment=True,sale_order=sale_orders).action_register_payment()
                    total_qty_ordered = sum(line.product_uom_qty for line in self.sale_id.order_line)
                    total_qty_invoiced = sum(move_line.quantity for move_line in account_moves.invoice_line_ids)
                    existing_transaction = self.env['payment.transaction'].search([
                        ('reference', '=', sale_orders.name),
                        ('state', '=', 'authorized')
                    ], limit=1)
                    if existing_transaction:
                        account_moves.payment_action_capture()
                    if not total_qty_invoiced != total_qty_ordered and not existing_transaction:

                        account_moves.with_context(auto_inv_payment=True,
                                                   sale_order=sale_orders).action_register_payment()
                    elif not existing_transaction:
                        account_moves.with_context(auto_inv_payment=True,
                                                   sale_order=sale_orders).action_register_payment()
                if account_moves:
                    picking.write({'account_move_ids': [(6, 0, account_moves.ids)]})
