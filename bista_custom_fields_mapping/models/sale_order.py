# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, api, fields, _


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    cancel_done_picking = fields.Boolean(string='Cancel Done Delivery?', compute='check_cancel_done_picking')
    physical_address = fields.Text(string='Address', compute='get_address')

    other_users = fields.Many2many(string='Additional Salesperson', comodel_name='res.users')
    user_count = fields.Integer(compute='_compute_total_user', store=True)
    po_count = fields.Integer(compute="_compute_po_count", string='PO Count', copy=False, default=0)

    @api.depends('name')
    def _compute_po_count(self):
        for order in self:
            purchase_count = self.env['purchase.order'].search_count([('origin', 'like', order.name)])

            order.po_count = purchase_count


    @api.model
    def check_cancel_done_picking(self):
        for order in self:
            Flag = False
            if order.company_id.cancel_done_picking and order.delivery_count > 0:
                for picking in self.picking_ids:
                    if picking.state != 'cancel':
                        Flag = True
                        break
            order.cancel_done_picking = Flag

    @api.onchange('partner_id')
    def onchange_partner_id_address_show(self):
        if self.partner_id:
            self.physical_address = self.partner_id.contact_address

    def get_address(self):
        if self.partner_id:
            self.physical_address = self.partner_id.contact_address

    @api.depends('other_users', 'user_id')
    def _compute_total_user(self):
        for rec in self:
            if rec.other_users or rec.user_id:
                rec.user_count = len(rec.other_users.filtered(lambda x: x.active == True)) + len(
                    rec.user_id.filtered(lambda x: x.active == True))