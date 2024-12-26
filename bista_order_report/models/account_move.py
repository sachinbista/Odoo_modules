# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class AccountMove(models.Model):
	_inherit = 'account.move'
	
	sale_order_id = fields.Many2one('sale.order', string="Sale Order Ref")
	create_date = fields.Datetime(related='sale_order_id.create_date',
	                              string="Create Date")
	
	@api.model
	def create(self, vals):
		sale_order_obj = self.env['sale.order']
		if vals.get('invoice_origin', ''):
			so = sale_order_obj.search(
				[('name', 'like', vals['invoice_origin'])], limit=1)
			if so:
				vals.update({
					'sale_order_id': so.id,
				})
		return super(AccountMove, self).create(vals)
