# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class AccountMove(models.Model):
	_inherit = 'account.move'

	sale_ref_id = fields.Many2one('res.partner', string="Sales Representative")

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		self.sale_ref_id = self.partner_id.sale_ref_id