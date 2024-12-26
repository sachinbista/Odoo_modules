# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from datetime import date, datetime

class InheritPOSOrder(models.Model):
	_inherit = 'pos.order'

	sale_order_ids = fields.Many2many('sale.order',string="Imported Sale Order(s)")

	def _order_fields(self, ui_order):
		res = super(InheritPOSOrder, self)._order_fields(ui_order)
		config = self.env['pos.session'].browse(ui_order['pos_session_id']).config_id
		# import sale functionality
		
		if 'imported_sales' in ui_order and ui_order.get('imported_sales'):
			so = ui_order['imported_sales'].split(',')
			so.pop()
			so_ids = []
			sale_orders = []
			for odr in so:
				sale = self.env['sale.order'].browse(int(odr))
				if sale :
					so_ids.append(sale.id)
					sale_orders.append(sale)
			res.update({
				'sale_order_ids': [(6,0,so_ids)]
			})

			if config.cancle_order:
				for s in sale_orders:
					s._action_cancel()
				
		return res

	def create_sales_order(self, partner_id, orderlines,cashier_id):
		sale_object = self.env['sale.order']
		sale_order_line_obj = self.env['sale.order.line']
		order_id = sale_object.create({'partner_id': partner_id, 'user_id': cashier_id})
		for dict_line in orderlines:
			product_obj = self.env['product.product']
			product_dict = dict_line.get('product')

			product_tax = product_obj.browse(product_dict.get('id'))
			tax_ids = []
			for tax in product_tax.taxes_id:
				tax_ids.append(tax.id)

			product_name = product_obj.browse(product_dict.get('id')).name
			vals = {'product_id': product_dict.get('id'),
					'name': product_name,
					'product_uom_qty': product_dict.get('quantity'),
					'price_unit': product_dict.get('price'),
					'product_uom': product_dict.get('uom_id'),
					'tax_id': [(6, 0, tax_ids)],
					'discount': product_dict.get('discount'),
					'order_id': order_id.id}
			sale_order_line_obj.create(vals)					
		return order_id.name