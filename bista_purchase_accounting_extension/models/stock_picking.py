# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError
import re

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            if 'cancel_backorder' in self._context and self._context.get('cancel_backorder') == True:
                for move_id in picking.move_ids:
                    if move_id.state == 'cancel' and move_id.purchase_line_id:
                        move_id.purchase_line_id.manually_received_qty_uom = move_id.purchase_line_id.manually_received_qty_uom - move_id.product_uom_qty 
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for rec in self:
            if rec.picking_type_code == 'incoming':
                purchase_order_id = rec.move_ids.mapped('purchase_line_id').mapped('order_id')
                if len(purchase_order_id) > 1:
                    for purchase_order in purchase_order_id:
                        if rec.origin and rec.origin == purchase_order.name:
                            purchase_order_id = purchase_order

                landed_cost_id = self.env['stock.landed.cost'].search([('container_id', '=', rec.container_id), ('state', '=',  'confirmed'), ('po_ids', 'in',  purchase_order_id.id), ('picking_ids', 'in',  rec.id), ('target_model','=','purchase')], limit=1)
                if landed_cost_id:
                    raise UserError(_('You cannot cancel because %s landed cost is linked to this Picking. \n You must first unlink from landed costs!!') % landed_cost_id.display_name)
                
                partial_po_am_lst = []
                for move_id in rec.move_ids:
                    if move_id.purchase_line_id:
                        move_id.purchase_line_id.manually_received_qty_uom = move_id.purchase_line_id.manually_received_qty_uom - move_id.product_uom_qty 
                        svl_id = False
                        picking_am_vals = []
                        company_to =  move_id.mapped('move_line_ids.location_dest_id.company_id') or False
                        journal_id, acc_src, acc_dest, acc_valuation = move_id._get_accounting_data_for_valuation()
                        description = 'Cancel - ' + rec.name + ' - ' + rec.container_id
                        cost = move_id.purchase_line_id.price_unit * move_id.product_uom_qty
                        picking_am_vals.append(move_id.with_company(company_to).with_context(is_returned=True)._prepare_account_move_vals(acc_dest, acc_valuation, journal_id, move_id.product_uom_qty, description, svl_id, cost))
                        picking_am_ids = self.env['account.move'].sudo().create(picking_am_vals)._post()
                        picking_aml_ids = picking_am_ids.mapped('invoice_line_ids')
                        picking_total_debit = sum(line.debit for line in picking_am_ids.invoice_line_ids if not line.reconciled)
                        picking_total_credit = sum(line.credit for line in picking_am_ids.invoice_line_ids if not line.reconciled)

                        po_am_ids = move_id.purchase_line_id.mapped('purchase_extra_journal_entry')
                        po_aml_ids = po_am_ids.mapped('invoice_line_ids')
                        partial_po_am_lst.extend([po_aml_id.move_id.id for po_aml_id in po_aml_ids if not po_aml_id.reconciled and po_aml_id.matching_number == 'P' and po_aml_id.id not in partial_po_am_lst and rec.container_id in po_aml_id.move_id.ref and rec.origin in po_aml_id.move_id.ref and po_aml_id.move_id.state == 'posted'])
                        for po_am_id in po_am_ids:
                            if rec.container_id in po_am_id.ref and rec.origin in po_am_id.ref and po_am_id.state == 'posted':
                                reconcile_aml_lst = []
                                if po_am_id.id not in partial_po_am_lst:
                                    po_total_credit = sum(line.credit for line in po_am_id.invoice_line_ids)
                                    reconcile_aml_lst.extend([po_aml_id.id for po_aml_id in po_am_id.invoice_line_ids if po_aml_id.credit == picking_total_debit and not po_aml_id.reconciled])
                                    reconcile_aml_lst.extend([picking_aml_id.id for picking_aml_id in picking_aml_ids if picking_aml_id.debit == po_total_credit and not picking_aml_id.reconciled])
                                
                                if po_am_id.id in partial_po_am_lst:
                                    move_ids = self.env['stock.picking'].search([('origin', '=', rec.origin),('container_id', '=', rec.container_id),('state', '=', 'done')]).mapped('move_ids')
                                    for move_id in move_ids:
                                        reconciled_total = move_id.quantity_done * move_id.purchase_line_id.price_unit
                                        po_total_credit = sum(line.credit for line in po_am_id.invoice_line_ids)
                                        po_total_debit = sum(line.debit for line in po_am_id.invoice_line_ids)
                                        if po_total_credit == po_total_debit:
                                            reconcile_total = po_total_debit - reconciled_total
                                            po_reconcile_total = reconcile_total + reconciled_total
                                            reconcile_aml_lst.extend([po_aml_id.id for po_aml_id in po_am_id.invoice_line_ids if not po_aml_id.reconciled and po_aml_id.matching_number == 'P' and (po_aml_id.debit == po_reconcile_total or po_aml_id.credit == po_reconcile_total)]) 
                                            reconcile_aml_lst.extend([picking_aml_id.id for picking_aml_id in picking_aml_ids if picking_aml_id.credit == reconcile_total and not picking_aml_id.reconciled])
                                
                                if reconcile_aml_lst:
                                    reconcile_aml_ids = self.env['account.move.line'].browse(reconcile_aml_lst).reconcile()
                
        return res
   
