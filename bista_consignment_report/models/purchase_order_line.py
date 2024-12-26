# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from odoo.tools import groupby


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move=move)
        consignment_account_id = self.env['ir.config_parameter'].sudo().get_param('bista_consignment_report.consignment_account_id')
        if res and 'purchase_line_id' in res:
            stock_move_line = self.env['stock.move.line'].search([('move_id.purchase_line_id','=',res.get('purchase_line_id')),('owner_id','!=',False),('product_id','=',res.get('product_id')),('move_id.state','=','done')])
            for stock_move in stock_move_line.mapped('move_id').filtered(lambda s: s.consignment_stock_move):
                res.update({
                    'account_id': consignment_account_id,
                    })
        return res

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """

        if 'purchase_line' in self._context:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

            # 1) Prepare invoice vals and clean-up the section lines
            invoice_vals_list = []
            sequence = 10
            context = self._context
            order_line = context.get('purchase_line')
            for order in self:
                if order.invoice_status != 'to invoice':
                    continue

                order = order.with_company(order.company_id)
                pending_section = None
                # Invoice values.
                invoice_vals = order._prepare_invoice()
                # Invoice line values (keep only necessary sections).
                for line in order_line:
                    if line.display_type == 'line_section':
                        pending_section = line
                        continue
                    if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                        if pending_section:
                            line_vals = pending_section._prepare_account_move_line()
                            line_vals.update({'sequence': sequence})
                            invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                            sequence += 1
                            pending_section = None
                        line_vals = line._prepare_account_move_line()
                        if 'move_ids' in self._context:
                            for move_line in self._context['move_ids'].move_line_ids.filtered(lambda s: s.product_id.id == line_vals['product_id']):
                                line_vals.update({
                                    'quantity': move_line.qty_done
                                    })

                            purchase_move = self.env['stock.move'].search([('purchase_line_id','=',line.id)])
                            move_line = self.env['stock.move.line'].search([('move_id','in',self._context['move_ids'].ids)])
                            qty_done = 0
                            for pmove in purchase_move:
                                for mline in move_line.filtered(lambda s: s.product_id.id == line_vals['product_id'] and s.owner_id.id==pmove.restrict_partner_id.id):
                                    qty_done+= mline.qty_done
                                    line_vals.update({
                                        'quantity': qty_done
                                        })

                        line_vals.update({'sequence': sequence})
                        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                        sequence += 1
                invoice_vals_list.append(invoice_vals)

            if not invoice_vals_list:
                raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

            # 2) group by (company_id, partner_id, currency_id) for batch creation
            new_invoice_vals_list = []
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

            # 3) Create invoices.
            moves = self.env['account.move']
            AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
            for vals in invoice_vals_list:
                moves |= AccountMove.with_company(vals['company_id']).create(vals)

            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

            return self.action_view_invoice(moves)
        else:
            return super(PurchaseOrder, self).action_create_invoice()