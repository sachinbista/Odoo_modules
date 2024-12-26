# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sale Order'

    sale_ref_id = fields.Many2one('res.partner', string="Sales Rep", domain=[('is_sale_ref', '=', True)])
    auto_invoice = fields.Boolean(string='Auto Invoice', related='payment_term_id.auto_invoice')
    sale_ref_readonly = fields.Boolean(string='Sale Ref Readonly', compute='_compute_sale_ref_readonly')

    @api.depends('user_id')
    def _compute_sale_ref_readonly(self):
        for order in self:
            order.sale_ref_readonly = not self.env.user.has_group('sales_team.group_sale_manager')

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.sale_ref_id = self.partner_id.sale_ref_id






