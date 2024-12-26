# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import logging
from odoo import api, fields, models
from datetime import date
from odoo.tools import float_compare, float_is_zero
from odoo.tools.misc import groupby
from odoo.addons.purchase_stock.models.account_invoice import AccountMove

_logger = logging.getLogger(__name__)


class Accountmove(models.Model):
    _inherit = "account.move"

    @api.model
    def default_get(self, fields_list):
        res = super(Accountmove, self).default_get(fields_list)
        res['invoice_date'] = date.today() if 'invoice_date' in fields_list else None
        return res

    def write(self, vals):
        res = super(Accountmove, self).write(vals)
        if vals.get('invoice_date'):
            self.date = vals.get('invoice_date')
        return res

    inter_company_invoice_parent_change = fields.Boolean(string="Inter Company Parent Invoice Change", default=False,
                                                         tracking=True)

    def _fetch_duplicate_supplier_reference(self, only_posted=False):
        """
            This function is added for: while creating BackOrder scenario, raising warning for Duplicate Bills.
            so, returned {} when vendor bill is going to generate from Backorder Transfer.

            :return: {} when sale order is auto-generated & transfer is backorder.
            @author: Ashish Ghadi @Bista Solutions Pvt. Ltd.
        """
        if self._context.get('active_model') == 'sale.order' and self._context.get('default_origin'):
            sale_id = self.env['sale.order'].search([('name', '=', self._context.get('default_origin'))], limit=1)
            if sale_id and sale_id.picking_ids.filtered(lambda x: x.backorder_id) and sale_id.auto_generated:
                return {}

        return super(Accountmove, self)._fetch_duplicate_supplier_reference(only_posted)

    @api.model
    def action_reset_parent_invoice_change(self):

        """
            This function is used to change below field to 'False' when server action is called inside Vendor Bill
            for Soft Warning.

            :return:
            @author: Ashish Ghadi @Bista Solutions Pvt. Ltd.
        """
        for record in self:
            record.inter_company_invoice_parent_change = False

    def action_post(self):
        """
            This function is added to post Invoice with context 'auto_validate_vendor_bill'.

            :return:
            @author: Ashish Ghadi @Bista Solutions Pvt. Ltd.
        """
        for rec in self:
            if rec.move_type != 'entry':
                if rec.invoice_date != rec.date and not rec.env.context.get('is_invoice_date'):
                    return {
                        "type": "ir.actions.act_window",
                        "name": "Invoice Date",
                        "res_model": "invoice.date.wizard",
                        "view_mode": "form",
                        "target": "new",
                        "context": {'default_move_id': rec.id}
                    }
                if 'out_invoice' in rec.mapped('move_type') and not rec._context.get('auto_validate_vendor_bill', []):
                    return super(Accountmove, self).with_context({'auto_validate_vendor_bill': True}).action_post()
            return super(Accountmove, self).action_post()


def _post(self, soft=True):
    if not self._context.get('move_reverse_cancel'):
        self.env['account.move.line'].create(self._stock_account_prepare_anglo_saxon_in_lines_vals())

    # Create correction layer and impact accounts if invoice price is different
    stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
    valued_lines = self.env['account.move.line'].sudo()
    for invoice in self:
        if invoice.sudo().stock_valuation_layer_ids:
            continue
        if invoice.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            valued_lines |= invoice.invoice_line_ids.filtered(
                lambda l: l.product_id and l.product_id.cost_method != 'standard')
    if valued_lines:
        svls, _amls = valued_lines._apply_price_difference()
        if svls:
            stock_valuation_layers |= svls

    for (product, company), dummy in groupby(stock_valuation_layers, key=lambda svl: (svl.product_id, svl.company_id)):
        product = product.with_company(company.id)
        if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
            product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl})

    if stock_valuation_layers:
        stock_valuation_layers._validate_accounting_entries()

    posted = super(AccountMove,self)._post(soft)
    # The invoice reference is set during the super call
    for layer in stock_valuation_layers:
        description = f"{layer.account_move_line_id.move_id.display_name} - {layer.product_id.display_name}"
        layer.description = description
        if layer.product_id.valuation != 'real_time':
            continue
        layer.account_move_id.ref = description
        layer.account_move_id.line_ids.write({'name': description})

    return posted
AccountMove._post = _post
