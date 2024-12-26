# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
# 
#################################################################################
from  odoo import api,fields,models

class PosOrder(models.Model):
	_inherit = 'pos.order'

	customer_signature = fields.Binary(string='Customer Signature',readonly=True)

	@api.model
	def _order_fields(self,ui_order):
		fields_return = super(PosOrder,self)._order_fields(ui_order)
		fields_return.update({'customer_signature':ui_order.get('customer_signature','')})
		return fields_return