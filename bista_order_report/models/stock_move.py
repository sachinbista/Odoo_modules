# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class StockMove(models.Model):
	_inherit = 'stock.move'
	
	state_id = fields.Many2one('res.country.state',
	                           related='partner_id.state_id', store=True)
	delivered_subtotal = fields.Float(string='Delivered Subtotal',
	                                  compute="compute_subtotal")
	currency_id = fields.Many2one('res.currency', string="Currency",
	                              related='company_id.currency_id',
	                              default=lambda
		                              self:
	                              self.env.user.company_id.currency_id.id)
	
	@api.depends('quantity_done')
	def compute_subtotal(self):
		for rec in self:
			rec.delivered_subtotal = rec.quantity_done * rec.product_id.list_price
