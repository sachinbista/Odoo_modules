# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


class AccountPaymentFilterWizard(models.TransientModel):
	_name = 'account.payment.filter.wizard'
	_description = 'Account Payment Filter Wizard'
	
	date = fields.Date(string='Date', required=True)
	
	def filter_payments(self):
		payments = self.env['account.payment'].search(
			[('date', '=', self.date)])
		action = self.env["ir.actions.act_window"]._for_xml_id(
            "bista_payments.action_account_payment_bista_payments")
		action['domain'] = [('id', 'in', payments.ids)]
		action['target'] = 'current'
		return action
