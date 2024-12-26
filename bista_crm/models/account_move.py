# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        if self.line_ids and self.line_ids.purchase_line_id and \
           self.line_ids.purchase_line_id.order_id.trade_option !='regular':
           self.update({
            'state':'posted'
            })
           self._stock_account_anglo_saxon_reconcile_valuation()
        else:
            return super(AccountMove, self)._post(soft=soft)

    def _stock_account_get_last_step_stock_moves(self):
        """ Overridden from stock_account.
        Returns the stock moves associated to this invoice."""
        rslt = super(AccountMove, self)._stock_account_get_last_step_stock_moves()
        for invoice in self.filtered(lambda x: x.move_type == 'out_refund'):
            rslt += invoice.mapped('invoice_line_ids.purchase_line_id.move_ids').filtered(lambda x: x.state == 'done' and x.location_id.usage == 'supplier')
        return rslt

    def _stock_account_anglo_saxon_reconcile_valuation(self, product=False):
        res = super(AccountMove, self)._stock_account_anglo_saxon_reconcile_valuation(
            product=product)
        trade_account = int(self.env['ir.config_parameter'].get_param('bista_crm.trade_account_id'))
        for move in self:
            if not move.is_invoice():
                continue
            if not move.company_id.anglo_saxon_accounting:
                continue

            stock_moves = move._stock_account_get_last_step_stock_moves()
            # In case we return a return, we have to provide the related AMLs so all can be reconciled
            stock_moves |= stock_moves.origin_returned_move_id

            if not stock_moves:
                continue

            products = product or move.mapped('invoice_line_ids.product_id')
            for prod in products:
                if prod.valuation != 'real_time':
                    continue

                # We first get the invoices move lines (taking the invoice and the previous ones into account)...
                product_accounts = prod.product_tmpl_id._get_product_accounts()
                if move.is_sale_document():
                    if move.mapped('invoice_line_ids.purchase_line_id').order_id.trade_option !='regular':
                        product_interim_account = self.env['account.account'].browse(trade_account) if trade_account > 0 else product_accounts['stock_output']
                    else:
                         product_interim_account = product_accounts['stock_output']
                else:
                    product_interim_account = product_accounts['stock_input']
                if product_interim_account.reconcile:
                    # Search for anglo-saxon lines linked to the product in the journal entry.
                    product_account_moves = move.line_ids.filtered(
                        lambda line: line.product_id == prod and line.account_id == product_interim_account and not line.reconciled)

                    # Search for anglo-saxon lines linked to the product in the stock moves.
                    product_stock_moves = stock_moves._get_all_related_sm(prod)
                    product_account_moves |= product_stock_moves._get_all_related_aml().filtered(
                        lambda line: line.account_id == product_interim_account and not line.reconciled and line.move_id.state == "posted"
                    )

                    stock_aml = product_account_moves.filtered(lambda aml: aml.move_id.sudo().stock_valuation_layer_ids.stock_move_id)
                    invoice_aml = product_account_moves.filtered(lambda aml: aml.move_id == move)
                    correction_amls = product_account_moves - stock_aml - invoice_aml
                    # Reconcile.
                    if correction_amls:
                        if sum(correction_amls.mapped('balance')) > 0:
                            product_account_moves.with_context(no_exchange_difference=True).reconcile()
                        else:
                            (invoice_aml | correction_amls).with_context(no_exchange_difference=True).reconcile()
                            (invoice_aml.filtered(lambda aml: not aml.reconciled) | stock_aml).with_context(no_exchange_difference=True).reconcile()
                    else:
                        product_account_moves.reconcile()
        return res
