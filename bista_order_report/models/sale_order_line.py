# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'
	
	date_order = fields.Datetime(string="Order Date",
	                             related="order_id.date_order", store=True)
	user_id = fields.Many2one(string="Salesperson", related="order_id.user_id",
	                          store=True)
	commitment_date = fields.Datetime(string="Delivery Date",
	                                  related="order_id.commitment_date",
	                                  store="True")
	delivered_subtotal = fields.Monetary(string='Delivered Subtotal',
	                                     compute="compute_delivered_subtotal")
	currency_id = fields.Many2one('res.currency', string="Currency",
	                              related='company_id.currency_id',
	                              default=lambda
		                              self: self.env.user.company_id.currency_id.id)
	qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver',
	                              digits='Product Unit of Measure', store=True)
	
	@api.depends('qty_to_deliver')
	def compute_delivered_subtotal(self):
		for rec in self:
			rec.delivered_subtotal = rec.price_unit * rec.qty_to_deliver
