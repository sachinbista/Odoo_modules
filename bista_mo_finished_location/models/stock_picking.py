##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class StockPicking(models.Model):
	_inherit = 'stock.picking'

	hide_backorder = fields.Boolean(string="Hide Backorder",
									related="picking_type_id.hide_backorder")

	def button_validate(self):
		for rec in self:
			if rec.picking_type_id.is_auto_mo_close:
				for group in rec.group_id:
					mrp_id = self.env['mrp.production'].search(
						[('procurement_group_id', '=', group.id)])
					total_quantity_done = sum(
						move_id.quantity_done for move_id in rec.move_ids)
					if mrp_id and rec.picking_type_id.is_auto_mo_close:
						change_production_qty = self.env['change.production.qty']
						change_qty_vals = {
							'mo_id': mrp_id.id,
							'product_qty': total_quantity_done}
						change_qty_wizard = change_production_qty.create(
							change_qty_vals)
						change_qty_wizard.change_prod_qty()
					res = super(StockPicking, self).button_validate()
					if mrp_id and rec.picking_type_id.is_auto_mo_close:
						immediateproduction = self.env['mrp.immediate.production']
						imm_vals = {'mo_ids': [(4, mrp_id.id)],
									'immediate_production_line_ids': [(0, 0, {
										'to_immediate': True, 'production_id': mrp_id.id})]
									}
						imm_prod = immediateproduction.create(imm_vals)
						imm_prod.process()
						mrp_id.button_mark_done()
						if mrp_id.product_id.tracking != 'none':
							mrp_id.action_generate_serial()
			else:
				res = super(StockPicking, self).button_validate()
			return res


class StockPickingType(models.Model):
	_inherit = 'stock.picking.type'

	is_auto_mo_close = fields.Boolean(string="Is Auto Mo Close")
	hide_backorder = fields.Boolean(string="Hide Backorder")


class StockBackorderConfirmation(models.TransientModel):
	_inherit = 'stock.backorder.confirmation'

	hide_backorder = fields.Boolean(string="Hide Backorder",
									related="pick_ids.hide_backorder")

	# def process_cancel_backorder(self):
	# 	origin = self.pick_ids.origin
	# 	mrp_id = self.env['mrp.production'].search([('name', '=', origin)],
	# 											   limit=1)
	# 	total_quantity_done = sum(
	# 		move_id.quantity_done for move_id in self.pick_ids.move_ids)
	# 	if self.pick_ids.picking_type_id.is_auto_mo_close and mrp_id.product_qty > total_quantity_done:
	# 		change_production_qty = self.env['change.production.qty']
	# 		change_qty_vals = {
	# 			'mo_id': mrp_id.id,
	# 			'product_qty': total_quantity_done}
	# 		change_qty_wizard = change_production_qty.create(change_qty_vals)
	# 		change_qty_wizard.change_prod_qty()
	# 	res = super(StockBackorderConfirmation, self).process_cancel_backorder()
	# 	if self.pick_ids.picking_type_id.is_auto_mo_close and mrp_id:
	# 		if mrp_id.product_id.tracking in ('serial', 'lot'):
	# 			mrp_id.action_generate_serial()
	# 		immediateproduction = self.env['mrp.immediate.production']
	# 		imm_vals = {'mo_ids': [(4, mrp_id.id)],
	# 					'immediate_production_line_ids':
	# 						[(0, 0, {'to_immediate': True,
	# 								 'production_id': mrp_id.id})]
	# 					}
	# 		imm_prod = immediateproduction.create(imm_vals)
	# 		imm_prod.process()
	# 		mrp_id.button_mark_done()
	# 	return res
