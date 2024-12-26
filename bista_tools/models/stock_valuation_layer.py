# -*- coding: utf-8 -*-
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)

from odoo import models, fields, api, _


class StockMoveLayer(models.Model):
    _inherit = 'stock.valuation.layer'


    def _validate_accounting_entries(self):
        am_vals = []
        if self.env.user.has_group("bista_tools.admin_maintenance"):
            for svl in self:
                if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
                    continue
                if svl.currency_id.is_zero(svl.value):
                    continue
                move = svl.stock_move_id
                if not move:
                    move = svl.stock_valuation_layer_id.stock_move_id
                am_vals += move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
            # if am_vals:
            #     account_moves = self.env['account.move'].sudo().create(am_vals)
            #     account_moves._post()
            for svl in self:
                # Eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
                if svl.company_id.anglo_saxon_accounting:
                    svl.stock_move_id._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=svl.product_id)
        else:
            return super(StockMoveLayer, self)._validate_accounting_entries()

