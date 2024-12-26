# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	want_to_send_email = fields.Boolean(string="Want To Send Email ?")
	email_sent = fields.Boolean(string="Email Sent")

	# @api.model
	# def send_payment_reminders(self):
	# 	current_company_id = self.env.user.company_id.id
	# 	if current_company_id == 1:
	# 		domain = [('company_id', '=', current_company_id),
	# 				  ('want_to_send_email', '=', True)]
	# 		payments = self.env['account.payment'].search_read(domain, ['name',
	# 																	'partner_id'])
	# 		payments_sorted = sorted(payments, key=lambda x: x['name'])
	#
	# 		grouped_payments = {}
	# 		for payment in payments_sorted:
	# 			customer_id = payment['partner_id'][0]
	# 			if customer_id not in grouped_payments:
	# 				grouped_payments[customer_id] = []
	# 			grouped_payments[customer_id].append(payment)
	# 		for customer_id, customer_payments in grouped_payments.items():
	# 			customer = self.env['res.partner'].browse(customer_id)
	#
	# 			email_body = (f"Hello {customer.name},<br>Your payment for the "
	# 						  f"following Payment References: ")
	#
	# 			attachment_list = []
	# 			for payment in customer_payments:
	# 				try:
	# 					report = self.env['ir.actions.report'].sudo().search(
	# 						[(
	# 						 'report_name', '=',
	# 						 'account.report_payment_receipt')],
	# 						limit=1)
	#
	# 					if report:
	# 						pdf_content, format = self.env[
	# 							'ir.actions.report'].sudo()._render_qweb_pdf(
	# 							res_ids=payment['id'], report_ref=report)
	#
	# 						attachment_data = {
	# 							'name': f"Payment_{payment.get('name')}.pdf",
	# 							'datas': base64.b64encode(pdf_content),
	# 							'res_model': 'mail.compose.message',
	# 							'type': 'binary',
	# 						}
	#
	# 						attachment_id = self.env['ir.attachment'].sudo().create(
	# 							attachment_data)
	# 						attachment_list.append(attachment_id.id)
	# 					else:
	# 						raise UserError(
	# 							_("Payment report not found. Please check if the "
	# 							  "report exists."))
	#
	# 				except Exception as e:
	# 					raise UserError(
	# 						_("Error while generating and attaching payment "
	# 						  "report: %s" % str(
	# 							e)))
	#
	# 			payment_references = ', '.join(
	# 				payment['name'] for payment in customer_payments)
	# 			print("payment_referencespayment_r111111111111111111eferences",payment_references)
	# 			email_body += payment_references
	# 			email_body += " is pending."
	#
	# 			template_id = self.env.ref(
	# 				'bista_reports.email_template_account_payment').id
	# 			template = self.env['mail.template'].browse(template_id)
	# 			template.send_mail(self.id,
	# 							   force_send=True,
	# 							   email_values={'email_to': customer.email,
	# 											 'body_html': email_body,
	# 											 'attachment_ids': [
	# 												 (6, 0, attachment_list)]
	# 											 }
	# 							   )
	#
	# 			for payment in payments:
	# 				payment_id = payment['id']
	# 				payment_sent_email = self.env['account.payment'].search(
	# 					[('id', '=', payment_id)])
	# 				if payment_sent_email:
	# 					payment_sent_email.write({'want_to_send_email': False,
	# 											  'email_sent': True})

	# @api.model
	# def send_payment_reminders(self):
	# 	domain = [
	# 		('company_id', '=', 1),
	# 		('want_to_send_email', '=', True)
	# 	]
	# 	payments = self.env['account.payment'].search_read(domain, ['name', 'partner_id'])
	# 	payments_sorted = sorted(payments, key=lambda x: x['name'])
	#
	# 	grouped_payments = {}
	# 	for payment in payments_sorted:
	# 		customer_id = payment['partner_id'][0]
	# 		if customer_id not in grouped_payments:
	# 			grouped_payments[customer_id] = []
	# 		grouped_payments[customer_id].append(payment)
	#
	# 	for customer_id, customer_payments in grouped_payments.items():
	# 		customer = self.env['res.partner'].browse(customer_id)
	#
	# 		email_body = (
	# 			f"Hello {customer.name},<br>"
	# 			f"Your payment for the following Payment References: "
	# 		)
	#
	# 		attachment_list = []
	# 		for payment in customer_payments:
	# 			try:
	# 				report = self.env['ir.actions.report'].sudo().search(
	# 					[('report_name', '=', 'account.report_payment_receipt')],
	# 					limit=1
	# 				)
	#
	# 				if report:
	# 					pdf_content, format = report.sudo()._render_qweb_pdf(
	# 						res_ids=payment['id'],report_ref=report
	# 					)
	#
	# 					attachment_data = {
	# 						'name': f"Payment_{payment['name']}.pdf",
	# 						'datas': base64.b64encode(pdf_content),
	# 						'res_model': 'mail.compose.message',
	# 						'type': 'binary',
	# 					}
	#
	# 					attachment_id = self.env['ir.attachment'].sudo().create(attachment_data)
	# 					attachment_list.append(attachment_id.id)
	# 				else:
	# 					raise UserError(_("Payment report not found. Please check if the report exists."))
	#
	# 			except Exception as e:
	# 				raise UserError(_("Error while generating and attaching payment report: %s" % str(e)))
	#
	# 		payment_references = ', '.join(payment['name'] for payment in customer_payments)
	# 		email_body += f"{payment_references} is pending."
	#
	# 		template = self.env.ref('bista_reports.email_template_account_payment')
	# 		template.send_mail(
	# 			self.id,
	# 			force_send=True,
	# 			email_values={
	# 				'email_to': customer.email,
	# 				'body_html': email_body,
	# 				'attachment_ids': [(6, 0, attachment_list)]
	# 			}
	# 		)
	#
	# 		payment_ids = [payment['id'] for payment in customer_payments]
	# 		payments_to_update = self.env['account.payment'].browse(payment_ids)
	# 		payments_to_update.write({
	# 			'want_to_send_email': False,
	# 			'email_sent': True
	# 		})
	# 		self.env.cr.commit()


	@api.model
	def send_payment_reminders(self):
		domain = [
			('want_to_send_email', '=', True),
			('payment_type','=','outbound')
		]
		payments = self.env['account.payment'].search_read(domain, ['name', 'partner_id'])
		payments_sorted = sorted(payments, key=lambda x: x['name'])

		grouped_payments = {}
		for payment in payments_sorted:
			if payment.get('partner_id'):
				customer_id = payment['partner_id'][0]
				if customer_id not in grouped_payments:
					grouped_payments[customer_id] = []
				grouped_payments[customer_id].append(payment)

		for customer_id, customer_payments in grouped_payments.items():
			customer = self.env['res.partner'].browse(customer_id)

			email_body = f"Dear {customer.name},<br><br>"
			email_body += "Please find below the payment details:<br><br>"

			email_body += """
	        <table border="1" style="border-collapse: collapse; width: 100%;">
	            <tr>
	            	<th style="padding: 8px; text-align: left;">Date</th>
	                <th style="padding: 8px; text-align: left;">Amount</th>
	                <th style="padding: 8px; text-align: left;">Bill Reference</th>
	                <th style="padding: 8px; text-align: left;">Payment Method</th>
	            </tr>
	        """

			for payment in customer_payments:
				payment_id = self.env['account.payment'].browse(payment['id'])
				date = payment_id.date.strftime("%m/%d/%Y")
				invoice_references = ', '.join(
					ref for ref in payment_id.reconciled_bill_ids.mapped('ref') if isinstance(ref, str)
				) or " "

				email_body += f"""
	            <tr>
	            	<td style="padding: 8px;">{date}</td>
	                <td style="padding: 8px;">{payment_id.company_id.currency_id.symbol}{payment_id.amount}</td>
	                <td style="padding: 8px;">{invoice_references}</td>
	                <td style="padding: 8px;">{payment_id.payment_method_line_id.name}</td>
	            </tr>
	            """

			email_body += "</table><br>"
			email_body += (
				"Please contact us if there are any discrepancies.<br><br>"
				"Thank you for your prompt attention to this matter."
			)

			template = self.env.ref('bista_reports.email_template_account_payment')
			template.send_mail(
				payment_id.id,
				force_send=True,
				email_values={
					'email_to': customer.email,
					'body_html': email_body,
				}
			)

			payment_ids = [payment['id'] for payment in customer_payments]
			payments_to_update = self.env['account.payment'].browse(payment_ids)
			payments_to_update.write({
				'want_to_send_email': False,
				'email_sent': True
			})
			self.env.cr.commit()

	@api.model
	def send_payment_reminders_customer(self):
		domain = [
			('want_to_send_email', '=', True),
			('payment_type', '=', 'inbound')
		]
		payments = self.env['account.payment'].search_read(domain, ['name', 'partner_id'])
		payments_sorted = sorted(payments, key=lambda x: x['name'])

		grouped_payments = {}
		for payment in payments_sorted:
			if payment.get('partner_id'):
				customer_id = payment['partner_id'][0]
				if customer_id not in grouped_payments:
					grouped_payments[customer_id] = []
				grouped_payments[customer_id].append(payment)

		for customer_id, customer_payments in grouped_payments.items():
			customer = self.env['res.partner'].browse(customer_id)

			email_body = f"Dear {customer.name},<br><br>"
			email_body += "Please find below the receipt for your payment:<br><br>"

			email_body += """
		        <table border="1" style="border-collapse: collapse; width: 100%;">
		            <tr>
		            	<th style="padding: 8px; text-align: left;">Date</th>
		                <th style="padding: 8px; text-align: left;">Amount</th>
		                <th style="padding: 8px; text-align: left;">Invoice Reference</th>
		                <th style="padding: 8px; text-align: left;">Payment Method</th>
		            </tr>
		        """

			for payment in customer_payments:
				payment_id = self.env['account.payment'].browse(payment['id'])
				date = payment_id.date.strftime("%m/%d/%Y")
				invoice_references = ', '.join(
					ref for ref in payment_id.reconciled_invoice_ids.mapped('name') if isinstance(ref, str)
				) or " "

				email_body += f"""
		            <tr>
		            	<td style="padding: 8px;">{date}</td>
		                <td style="padding: 8px;">{payment_id.company_id.currency_id.symbol}{payment_id.amount}</td>
		                <td style="padding: 8px;">{invoice_references}</td>
		                <td style="padding: 8px;">{payment_id.payment_method_line_id.name}</td>
		            </tr>
		            """

			email_body += "</table><br>"
			email_body += (
				"Please contact us if there are any discrepancies.<br><br>"
				"Thank you for your business."
			)

			template = self.env.ref('bista_reports.email_template_account_payment_customer')
			template.send_mail(
				payment_id.id,
				force_send=True,
				email_values={
					'email_to': customer.email,
					'body_html': email_body,
				}
			)

			payment_ids = [payment['id'] for payment in customer_payments]
			payments_to_update = self.env['account.payment'].browse(payment_ids)
			payments_to_update.write({
				'want_to_send_email': False,
				'email_sent': True
			})
			self.env.cr.commit()

	@api.model_create_multi
	def create(self, vals_list):
		res = super(AccountPayment, self).create(vals_list)
		for rec in res:
			if self.env.context.get('want_to_send_email', False):
				rec.want_to_send_email = True
		return res

	def button_change_date(self):
		payment_ids = self.search([('payment_type','=','inbound'),('company_id','=',4),('state','=','posted'),
								   ('journal_id','=',16),('is_reconciled','=',True),('date','=',"07/17/2024")])
		# payment_ids = self.search([('id', '=', 12855)])
		for payment in payment_ids:
			invoice_id = payment.reconciled_invoice_ids
			if payment.date != payment.reconciled_invoice_ids.invoice_date:
				payment.action_draft()
				payment.move_id.write(
					{'posted_before': False, 'secure_sequence_number': 0, 'sequence_number': 0, 'name': '/'})
				payment.write({'date': invoice_id.invoice_date})
				payment.action_post()
				invoice_aml_id = invoice_id.line_ids.filtered(
					lambda line: line.account_type in (
						'asset_receivable', 'liability_payable') and not line.reconciled)
				payment_aml_id = payment.move_id.line_ids.filtered(
					lambda line: line.account_type in (
						'asset_receivable', 'liability_payable') and not line.reconciled)
				line_to_rec = invoice_aml_id + payment_aml_id
				line_to_rec.reconcile()
