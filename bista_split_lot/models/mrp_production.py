# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class MrpProduction(models.Model):
	_inherit = 'mrp.production'

	def print_label(self):
		if self.product_id.detailed_type == 'product' and self.product_id.tracking != 'none':
			lot_id = self.lot_producing_id.ids or False
			if not lot_id:
				raise ValidationError(
					"Please enter Lot/Serial Number")
			action = self.env['ir.actions.act_window']._for_xml_id(
				'bista_zpl_labels.print_wizard_action')
			action['context'] = {'default_model': 'stock.lot',
			                     'default_lot_ids': [(6, 0, lot_id)]}
			return action
		elif self.product_id.tracking == 'none':
			# raise ValidationError("Please select tracking product.")
			product_id = self.product_id.ids or False
			action = self.env['ir.actions.act_window']._for_xml_id(
				'bista_zpl_labels.print_wizard_action')
			action['context'] = {'default_model': 'product.template',
								 'default_copies':self.product_qty,
								 'default_product_ids': [(6, 0, product_id)]}
			return action