# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class AccountMove(models.Model):
	_inherit = 'account.move'

	sale_ref_id = fields.Many2one('res.partner', string="Sales Representative",domain=[('is_sale_ref', '=', True)])
	sale_ref_readonly = fields.Boolean(string='Sale Ref Readonly', compute='_compute_sale_ref_readonly')

	@api.depends('user_id')
	def _compute_sale_ref_readonly(self):
		for order in self:
			order.sale_ref_readonly = not self.env.user.has_group('sales_team.group_sale_manager')

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		self.sale_ref_id = self.partner_id.sale_ref_id

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			invoice_origin = vals.get('invoice_origin')
			if invoice_origin:
				sale_order_id = self.env['sale.order'].search([('name', '=', invoice_origin)], limit=1)
				if sale_order_id:
					vals['sale_ref_id'] = sale_order_id.sale_ref_id.id
		return super().create(vals_list)

