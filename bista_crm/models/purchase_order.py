# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _



class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_opportunity_id = fields.Many2one('crm.lead', 'Opportunity')
    trade_option = fields.Selection([('regular', 'Regular'),('Trade In', 'Trade In/Up')], default="regular", string='Trade Option')
    bs_invoice_count = fields.Integer(related="invoice_count", string='Credit Note')

    @api.onchange('trade_option')
    def button_string_char(self):
        if self.trade_option == 'regular':
            self.update({
                'picking_type_id': self.env.ref('stock.picking_type_in').id
                })

        else:
            self.update({
                'picking_type_id': self.env.ref('bista_crm.trade_in_picking_type').id
                })


    def action_create_credit_note(self):
        context = self._context.copy()
        journal_id = self.env['account.journal'].search([('type', '=', 'sale'), ('active', '=', True)], limit=1)
        for rec in self.filtered(lambda  s: s.trade_option !='regular'):
            context.update({
                'default_move_type': 'out_refund',
                'default_journal_id': journal_id.id
            })
            rec.with_context(context).action_create_invoice()


    @api.depends('order_line.move_ids.picking_id', 'order_line.move_ids.move_dest_ids.picking_id')
    def _compute_picking_ids(self):
        super(PurchaseOrder, self)._compute_picking_ids()
        for order in self:
            if order.order_line.move_ids and order.order_line.move_ids.move_dest_ids:
                order.picking_ids += order.order_line.move_ids.move_dest_ids.mapped('picking_id')



