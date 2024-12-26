# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    po_reference = fields.Char('PO Reference', copy=False)


    def _stock_account_anglo_saxon_reconcile_valuation(self, product=False):
        res = super(AccountMove, self)._stock_account_anglo_saxon_reconcile_valuation(
            product=product)
        for move in self:
            stock_moves = move._stock_account_get_last_step_stock_moves()
            po_line_entry = stock_moves.mapped('purchase_line_id').mapped('purchase_extra_journal_entry').filtered(lambda s: s.state =='posted').mapped('line_ids')
            credit_entry = po_line_entry.filtered(lambda s: s.credit > 0 and not s.reconciled)
            debit_entry = po_line_entry.filtered(lambda s: s.debit > 0 and not s.reconciled)
            get_moves = stock_moves._get_all_related_aml()
            reconcile_credit_move = credit_entry + get_moves.filtered(lambda s: s.account_id.id in (
                credit_entry.mapped('account_id').ids) and s.debit > 0 and not s.reconciled)
            reconcile_debit_move = debit_entry + get_moves.filtered(lambda s: s.account_id.id in (
                debit_entry.mapped('account_id').ids) and s.credit > 0 and not s.reconciled)
            reconcile_debit_move.reconcile()
            for credit_line in reconcile_credit_move:
                for debit_line in reconcile_debit_move:
                    matching_number = debit_line.matching_number
                    credit_line.update({'matching_number': matching_number,'reconciled': True})
        return res

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.stock_move_id and x.stock_move_id.purchase_line_id and x.stock_move_id.purchase_line_id.purchase_extra_journal_entry):
            rslt += invoice.mapped('stock_move_id').filtered(lambda s: s.state=='done' and s.location_id.usage == 'supplier')
        return rslt
