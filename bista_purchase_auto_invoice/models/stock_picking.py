# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, api
from odoo.tools.misc import get_lang
import json


class Picking(models.Model):
    _inherit = "stock.picking"

    def create_picking_invoice(self, po_id):
        context = dict(self.env.context) or {}
        context.update({
            'active_model': 'purchase.order',
            'active_ids': po_id.ids,
            'active_id': po_id.id,
            'from_picking_po_validate': True
        })
        adv_invoice_id = self.env['purchase.advance.payment.inv'].with_context(
            context).create({
            'advance_payment_method': 'delivered',
            'deduct_pre_payments': True,
        })
        res = adv_invoice_id.create_invoices()
        if res and res.get('create_invoice_ids'):
            bill_ids = self.env['account.move'].sudo().browse(
                res.get('create_invoice_ids'))
            bill_ids.write({'invoice_date': self.scheduled_date})
            bill_ids.action_post()

    def button_validate(self):
        res = super(Picking, self).button_validate()
        for rec in self:
            if rec.move_line_ids and self.picking_type_id.code == 'incoming':
                move_lines = rec.move_line_ids.move_id.filtered(
                    lambda x: x.purchase_line_id and x.state == 'done')
                po_order = move_lines.mapped('purchase_line_id').mapped(
                    'order_id')
                if po_order:
                    rec.create_picking_invoice(po_id=po_order)
        return res
