# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    stock_transfer_id = fields.Many2one(
        'inter.company.stock.transfer')
    resupply_picking_id = fields.Many2one(
        'stock.picking', string="Picking Ref")

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        lines_vals_list = super(AccountMove, self)._stock_account_prepare_anglo_saxon_out_lines_vals()
        stock_transfer_id = self.stock_transfer_id
        if stock_transfer_id:
            for line in lines_vals_list:
                line_account_id = self.env['account.account'].sudo().browse(line['account_id'])
                if line_account_id.account_type == 'expense_direct_cost':
                    if self.move_type in ('out_invoice', 'out_refund'):
                        warehouse_account_id = (stock_transfer_id.warehouse_id and
                                                stock_transfer_id.warehouse_id.account_expense_id)
                        if warehouse_account_id:
                            line['account_id'] = warehouse_account_id.id
                    elif self.move_type in ('in_invoice', 'in_invoice'):
                        dest_warehouse_account_id = (stock_transfer_id.dest_warehouse_id and
                                                     stock_transfer_id.dest_warehouse_id.account_expense_id)
                        if dest_warehouse_account_id:
                            line['account_id'] = dest_warehouse_account_id.id
        return lines_vals_list

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.resupply_picking_id and x.stock_transfer_id):
            rslt += invoice.mapped('resupply_picking_id.move_ids').filtered(lambda x: x.state == 'done')
        return rslt


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_account_id(self):
        super(AccountMoveLine, self)._compute_account_id()
        for line in self:
            stock_transfer_id = line.move_id.stock_transfer_id
            move_type = line.move_id.move_type
            if stock_transfer_id:
                if move_type in ('out_invoice', 'out_refund'):
                    if (line.account_id.account_type == 'asset_receivable' and
                            stock_transfer_id.warehouse_id.account_receivable_id):
                        line.account_id = stock_transfer_id.warehouse_id.account_receivable_id.id
                elif move_type in ('in_invoice', 'in_refund'):
                    if (line.account_id.account_type == 'liability_payable' and
                            stock_transfer_id.dest_warehouse_id.account_payable_id):
                        line.account_id = stock_transfer_id.dest_warehouse_id.account_payable_id.id


class AccountPayment(models.Model):
    _inherit = "account.payment"

    stock_transfer_id = fields.Many2one(
        'inter.company.stock.transfer', 'Stock Transfer')
