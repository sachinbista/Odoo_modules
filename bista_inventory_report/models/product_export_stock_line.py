# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductExportStockLine(models.Model):
	_name = 'product.export.stock.line'
	
	product_id = fields.Many2one('product.product', string='Product ID',
	                             required=True)
	available_quantity = fields.Float(string='Available Quantity',
	                                  related='product_id.free_qty')
	product_export_id = fields.Many2one('product.template',
	                                    string='Product Export ID')
	
	@api.onchange('product_id')
	def _onchange_product_id(self):
		if self.product_id and self.product_id.is_export_stock:
			raise UserError(
				"You cannot add this product, as it an export stock product")
