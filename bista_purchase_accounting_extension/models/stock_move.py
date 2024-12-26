# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions
#    Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################
import re

from odoo import api, fields, models, _



class StockMove(models.Model):
    _inherit = "stock.move"


    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        res = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id,cost)
        res_config_obj = self.env['ir.config_parameter'].sudo()
        good_shipped_acc_id = res_config_obj.get_param('good_shipped_acc_id', default=False)
        bs_po_good_shipped_id = res_config_obj.get_param('bs_po_good_shipped_id', default=False)
        bs_po_good_shipped_id_str = str(bs_po_good_shipped_id)
        match = re.search(r'\((\d+),\)', bs_po_good_shipped_id_str)
        bs_po_good_shipped_id_value = int(match.group(1)) if match else None
        if self.purchase_line_id  and self.purchase_line_id.purchase_extra_journal_entry and bs_po_good_shipped_id_value and good_shipped_acc_id:
            credit_account_id = bs_po_good_shipped_id_value
            debit_account_id = good_shipped_acc_id
            if self._context.get('all_cancel') == True and self.picking_id.picking_type_code == 'incoming':
                description = 'Cancel - ' + self.picking_id.name + ' - ' + self.product_id.name
            new_data = self._prepare_account_move_line(qty, cost, int(credit_account_id), int(debit_account_id), svl_id, description)
            if self._context.get('all_cancel') == True and self.picking_id.picking_type_code == 'incoming':
                res['line_ids'] = new_data
                res['stock_move_id'] = self.id
            if 'all_cancel' not in self._context:
                res['line_ids']+= new_data
                if 'cancel_backorder' in self._context and self._context.get('cancel_backorder') == True and self.purchase_line_id and self.picking_id.picking_type_code == 'incoming':
                    cancel_move_ids = self.picking_id.move_ids.filtered(lambda move: move.state == 'cancel' and move.product_id.id == self.product_id.id and move.purchase_line_id.id == self.purchase_line_id.id)
                    cancel_qty = sum(cancel_move_ids.mapped('product_uom_qty'))
                    cancel_new_data = self._prepare_account_move_line(cancel_qty, self.purchase_line_id.price_unit * cancel_qty, int(credit_account_id), int(debit_account_id), svl_id, 'Cancel Back Order - ' + description)
                    res['line_ids']+= cancel_new_data

        return res

    def _get_related_invoices(self):
        """ Overridden to return the vendor bills related to this stock move.
        """
        rslt = super(StockMove, self)._get_related_invoices()
        if self.purchase_line_id and self.purchase_line_id.purchase_extra_journal_entry:
            invoices = self.env['account.move'].search([('stock_move_id','=',self.id)])
            rslt+= invoices.filtered(lambda s: s.state=='posted')
        return rslt

    def _search_picking_for_assignation_domain(self):
        domain = super(StockMove, self)._search_picking_for_assignation_domain()
        if 'active_model' in self._context and self._context.get('active_model') == 'purchase.order':
            purchase_order_ids = self.env['purchase.order'].browse(self.env.context.get('active_ids') if self.env.context.get('active_ids') else [])
            for purchase_order_id in purchase_order_ids:
                if purchase_order_id.last_container_status == 'container_exist':
                    domain += [('receive_by_container', '=', purchase_order_id.last_container)]

        return domain

    def _search_picking_for_assignation(self):
        picking = super(StockMove, self)._search_picking_for_assignation()
        # if self.picking_type_id.code !='internal' and self.move_orig_ids.picking_type_id.code =='incoming' and self.move_orig_ids.filtered(lambda s: s.picking_id.container_id):
        #     picking = False
        # elif self.move_orig_ids.filtered(lambda s: s.picking_type_id.code=='incoming' and s.picking_id.container_id):
        #     picking = False
        # elif self.move_orig_ids.move_orig_ids.filtered(lambda s: s.picking_id.container_id):
        #     picking = False
        if 'active_model' in self._context and self._context.get('active_model') == 'purchase.order':
            purchase_order_ids = self.env['purchase.order'].browse(
                self.env.context.get('active_ids') if self.env.context.get('active_ids') else [])
            for purchase_order_id in purchase_order_ids:
                if purchase_order_id.last_container_status == 'container_exist':
                    return picking
                else:
                    if purchase_order_id.last_container_status == 'new_container':
                        return False
        else:
            return picking