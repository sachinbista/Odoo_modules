# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, _

class ProductTemplate(models.Model):
	_inherit = "product.template"

	def action_open_quants(self):
		rec = super(ProductTemplate, self).action_open_quants()
		add_new_filter = {'search_default_available_stock': 1}
		rec['context'].update(add_new_filter)
		return rec

class ProductProduct(models.Model):
	_inherit = "product.product"

	def action_open_quants(self):
		rec = super(ProductProduct, self).action_open_quants()
		add_new_filter = {'search_default_available_stock': 1}
		rec['context'].update(add_new_filter)
		return rec
	
	
	
	 



