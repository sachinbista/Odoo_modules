# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError
from bs4 import BeautifulSoup

class Lead(models.Model):
    _inherit = "crm.lead"

    purchase_order_count = fields.Integer(compute='_compute_purchase_count', string="Number of Purchase Orders")
    purchase_order_ids = fields.One2many('purchase.order', 'purchase_opportunity_id', string='Purchase Orders')
    trade_option = fields.Selection([('regular', 'Regular'),('Trade In', 'Trade In/Up')], default="regular",string='Trade Option')

    def _compute_purchase_count(self):
        for lead in self:
            lead.purchase_order_count = len(lead.purchase_order_ids.filtered(lambda p: p.state != 'cancel'))

    def action_purchase_quotations_new(self):
        self.ensure_one()
        purchase_order = self.env['purchase.order']
        purchase_order_obj = self.env['purchase.order']
        if not self.partner_id:
            raise UserError("Please add Vendor to create Purchase Order.")
        else:
            existing_po = purchase_order_obj.search([('purchase_opportunity_id','=',self.id),('state','=','draft')],limit=1)
            if not existing_po:
                picking_type_id = self.env.ref('bista_crm.trade_in_picking_type')
                purchase_order |= purchase_order_obj.create({
                    'partner_id': self.partner_id.id,
                    'picking_type_id': picking_type_id.id,
                    'origin': self.name,
                    'trade_option': self.trade_option,
                    'purchase_opportunity_id': self.id,
                    'company_id': self.company_id.id or self.env.company.id,

                })
            else:
                purchase_order |= existing_po
            return {
                'type': 'ir.actions.act_window',
                'name': 'Purchase Order',
                'res_model': 'purchase.order',
                'res_id': purchase_order.id,
                'views': [(self.env.ref('purchase.purchase_order_form').id, 'form')],
                'view_mode': 'form',
                'context': {},
                'domain': [],
                'target': 'self'
            }

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("bista_crm.action_purchase_order_view")
        action['domain'] = [('purchase_opportunity_id', '=', self.id)]
        return action



