# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, ValidationError


class StockRoute(models.Model):
	_inherit = "stock.route"

	is_intercompany_route = fields.Boolean('Is Intercompany Route?')

	# @api.constrains('is_intercompany_route')
	# def _check_is_intercompany_route(self):
	# 	for rec in self:
	# 		if rec.is_intercompany_route:
	# 			search_rec_count = self.search_count(
	# 				[('is_intercompany_route', '=', True)])
	# 			if search_rec_count > 1:
	# 				raise ValidationError(
	# 					_('Only 1 route is configure as intercompany route'))
	# 	return True

class SaleOrder(models.Model):
	_inherit = "sale.order"

	@api.model_create_multi
	def create(self, vals_list):
		res = super(SaleOrder, self).create(vals_list)
		stock_route = self.env['stock.route']
		for rec in res:
			if rec.auto_generated:
				for line in rec.order_line:
					product_route_ids = stock_route.search([
						('is_intercompany_route', '=', True),
						('company_id', '=', self.env.company.id),
					])
					line_route_id = product_route_ids.filtered(
						lambda x: line.product_template_id.id in x.product_ids.ids)
					if line_route_id:
						line.route_id = line_route_id[0].id
		return res
