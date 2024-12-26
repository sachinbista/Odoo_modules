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


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    journal_entries_count = fields.Integer("Entries Count", compute='_compute_journal_entries_ids')
    last_container_status = fields.Char(string='Last Container Status', copy=False)
    last_container = fields.Char(string='Last Container', copy=False)

    def button_cancel(self):
        res = super().button_cancel()
        if self.env.context.get('fromwizard'):
            landed_cost_id = self.env['stock.landed.cost'].search([('po_ids', 'in', self.ids), ('state', 'in', ('draft', 'confirmed'))], limit=1)
            if landed_cost_id:
                raise UserError(_('You cannot cancel because %s landed cost is linked to this PO. \n You must first unlink from landed costs!!') % landed_cost_id.display_name)
            entry_ids =  self.order_line.mapped('purchase_extra_journal_entry')
            entry_ids.button_cancel()
        return res

    @api.depends('order_line.purchase_extra_journal_entry')
    def _compute_journal_entries_ids(self):
        for order in self:
            journal_entry = len(order.order_line.purchase_extra_journal_entry)
            order.journal_entries_count = journal_entry

    def action_view_entries(self):
        
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.order_line.mapped('purchase_extra_journal_entry').ids)],
        }

    # def create_entries(self):
    #     res_config_obj = self.env['ir.config_parameter'].sudo()
    #     good_shipped_acc_id = res_config_obj.get_param('good_shipped_acc_id', default=False)
    #     bs_po_good_shipped_id = res_config_obj.get_param('bs_po_good_shipped_id', default=False)
    #     match = re.search(r'\((\d+),\)', bs_po_good_shipped_id)
    #     bs_po_good_shipped_id_value = int(match.group(1)) if match else None
    #     if good_shipped_acc_id and bs_po_good_shipped_id:
    #         for po_line in self.order_line.filtered(lambda line: line.price_unit != 0 and line.product_id.detailed_type == 'product'
    #                                                 and line.product_id.categ_id.property_valuation != 'manual_periodic'):

    #             cost = po_line.manually_received_qty_uom * po_line.price_uni
    #             po_line._account_entry_move(po_line.manually_received_qty_uom,description, cost,int(good_shipped_acc_id),bs_po_good_shipped_id_value)

    def button_open_manual_receipt_wizard(self):
        res = super(PurchaseOrder, self).button_open_manual_receipt_wizard()
        res.update({
            'name':  _('Create Merchandise/ Container')
            })
        return res

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    purchase_extra_journal_entry = fields.Many2many(
        'account.move',
        string='Purchase Extra Journal Entry',
        readonly=True,
        copy=False,
        help='This field stores related purchase extra journal entries.'
    )

    def _account_entry_move(self, qty, description, cost, acc_src,acc_dest):
        """ Accounting Valuation Entries """
        self.ensure_one()
        am_vals = []
        accounts_data = self.sudo().product_id.product_tmpl_id.get_product_accounts()
        if not accounts_data.get('stock_journal', False):
            raise UserError(
                _('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts.'))
        journal_id = accounts_data['stock_journal'].id
        am_vals.append(self.sudo()._prepare_account_move_vals(acc_src,acc_dest,
                                            journal_id,
                                            qty,
                                            description,
                                            cost))
        if am_vals:
            account_moves = self.env['account.move'].sudo().create(am_vals)
            account_moves.sudo()._post()
            self.purchase_extra_journal_entry+=account_moves
        return am_vals

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description,cost):
        self.ensure_one()
        valuation_partner_id = self.order_id.partner_id
        move_ids = self.with_context({'inv_reference': self._context.get('inv_reference','')}).purchase_prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)
        date = self._context['date'] if 'date' in self._context else fields.Date.context_today(self)
        return {
            'journal_id': journal_id,
            'line_ids': move_ids,
            'partner_id': valuation_partner_id.id,
            'date': date,
            'ref': description,
            'move_type': 'entry',
            'is_storno': self.env.context.get('is_returned') and self.env.company.account_storno,
        }

    def purchase_prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, description):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.
        debit_value = self.order_id.company_id.currency_id.round(cost)
        credit_value = debit_value

        valuation_partner_id = self.order_id.partner_id.id
        if 'inv_reference' in self._context and self._context.get('inv_reference') !=False:
            description = self.order_id.name + "-" + self._context.get('inv_reference')
        else:
            description = self.order_id.name
        res = [(0, 0, line_vals) for line_vals in
               self._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value,
                                                   debit_account_id, credit_account_id, description).values()]

        return res

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
        # This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()
        debit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'balance': debit_value,
            'account_id': debit_account_id,
        }

        credit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'balance': -credit_value,
            'account_id': credit_account_id,
        }

        rslt = {'credit_line_vals': credit_line_vals, 'debit_line_vals': debit_line_vals}
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.env.context.get('price_diff_account')
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'balance': -diff_amount,
                'ref': description,
                'partner_id': partner_id,
                'account_id': price_diff_account.id,
            }
        return rslt