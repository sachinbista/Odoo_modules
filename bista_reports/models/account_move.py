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
from odoo.tools import formatLang


class AccountMove(models.Model):
	_inherit = 'account.move'
	
	want_to_send_email = fields.Boolean(string="Want To Send Email ?")
	email_sent = fields.Boolean(string="Email Sent")

	def accept_blue_card_no(self):
		card_no_list = []
		for line in self.accept_blue_details_id:
			if line.account_accept_move_id.id == self.id:
				if line.credit_card_no_encr:
					card_no = line.credit_card_no_encr
					card_no_list.append(card_no)
		return card_no_list

	# def action_post(self):
	# 	res=super(AccountMove,self).action_post()
	# 	attchment_ids=self.env['ir.attachment'].search([('res_id','=',self.id)])
	# 	if not attchment_ids:
	# 		report = self.env['ir.actions.report']._render_qweb_pdf(
	# 			"account.report_invoice_with_payments", self.id)
	# 	else:
	# 		attchment_ids.unlink()
	# 		report = self.env['ir.actions.report']._render_qweb_pdf(
	# 			"account.report_invoice_with_payments", self.id)
	#
	# 	return res
	
	@api.model
	def create(self, vals):
		sale_order_obj = self.env['sale.order']
		if vals.get('invoice_origin'):
			so = sale_order_obj.search(
				[('name', 'like', vals['invoice_origin'])], limit=1)
			# pick_ref = False
			# for pick in so.picking_ids.filtered(lambda l: l.picking_type_code == "outgoing"):
			# 	pick_ref = pick
			if so:
				vals.update({
					'sale_order_id': so.id,
					# 'picking_id':pick_ref and pick_ref.id or False,
				})
		return super(AccountMove, self).create(vals)

	def action_post(self):
		res = super(AccountMove, self).action_post()
		# code is use for get the invoice attachment in followup reports
		self.set_invoice_on_main_attachment()
		return res

	def set_invoice_on_main_attachment(self):
		for invoice in self:
			if not invoice.move_type =='entry':
				report = self.env['ir.actions.report'].sudo().search(
					[('report_name', '=', 'account.report_invoice')],
					limit=1)
				if report:
					pdf_content, format = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
						res_ids=invoice.id, report_ref=report)

					attachment_data = {
						'name': f"Invoice_{invoice.name}.pdf",
						'datas': base64.b64encode(pdf_content),
						'res_model': 'account.move',
						'type': 'binary',
						'res_id':invoice.id
					}
					attchment_ids = self.env['ir.attachment'].search([('res_id', '=', invoice.id)])
					for attachment in attchment_ids:
						attachment.unlink()
					new_attachment = self.env['ir.attachment'].sudo().create(
						attachment_data)
					invoice.message_main_attachment_id = new_attachment
				else:
					raise UserError(_("Invoice report not found. Please check if the report exists."))


	def action_set_invoice_on_main_attachment(self):
		for invoice in self:
			if not invoice.message_main_attachment_id:
				prioritary_attachments = invoice.attachment_ids.filtered(lambda x: x.mimetype.endswith('pdf'))
				if prioritary_attachments:
					main_attachment = prioritary_attachments[0]
					invoice.with_context(tracking_disable=True).sudo().write(
						{'message_main_attachment_id': main_attachment.id})
				else:
					invoice.set_invoice_on_main_attachment()

	
	@api.model
	def send_invoice_reminders(self):
		current_company_id = self.env.user.company_id.id
		domain = [('company_id', '=', current_company_id),
		          ('move_type', '=', 'out_invoice'),
		          ('want_to_send_email', '=', True)]
		invoices_id = self.env['account.move'].search_read(domain, ['name',
		                                                            'partner_id'])
		
		grouped_invoices = {}
		for invoice in invoices_id:
			customer_id = invoice['partner_id'][0]
			if customer_id not in grouped_invoices:
				grouped_invoices[customer_id] = []
			grouped_invoices[customer_id].append(invoice)
		
		for customer_id, customer_invoices in grouped_invoices.items():
			customer = self.env['res.partner'].browse(customer_id)
			
			email_body = f"Dear {customer.name},<br><br>"
			attachment_list = []
			
			for invoice in customer_invoices:
				try:
					report = self.env['ir.actions.report'].sudo().search(
						[('report_name', '=', 'account.report_invoice')],
						limit=1)
					
					if report:
						pdf_content, format = self.env[
							'ir.actions.report'].sudo()._render_qweb_pdf(
							res_ids=invoice['id'], report_ref=report)
						
						attachment_data = {
							'name': f"Invoice_{invoice.get('name')}.pdf",
							'datas': base64.b64encode(pdf_content),
							'res_model': 'mail.compose.message',
							'type': 'binary',
						}
						attachment_id = self.env['ir.attachment'].sudo(
						
						).create(
							attachment_data)
						attachment_list.append(attachment_id.id)
					else:
						raise UserError(
							_("Invoice report not found. Please check if the "
							  "report exists."))
				
				except Exception as e:
					raise UserError(
						_("Error while generating and attaching invoice "
						  "report: %s" % str(
							e)))
			
			invoice_numbers = ", ".join(
				invoice['name'] for invoice in customer_invoices)
			email_body += (f"Here are your invoices: {invoice_numbers}<br/><br "
			               f"/>Please remit payment at your earliest "
			               f"convenience.<br /><br />")
			email_body += ("Do not hesitate to contact us if you have any "
			               "questions.<br /><br />")
			email_body += ("If this invoice has not been received by its intended recipient,"
						   "please contact 4orders@premierprintsinc.com or call 662-840-4060 x222 to let us know."
			               "questions.")

			template_id = self.env.ref(
				'bista_reports.email_template_account_invoice').id
			template = self.env['mail.template'].browse(template_id)
			template.send_mail(self.id,
			                   force_send=True,
			                   email_values={'email_to': customer.email,
			                                 'body_html': email_body,
			                                 'attachment_ids': [
				                                 (6, 0, attachment_list)]}
			                   )
			for invoice in invoices_id:
				invoice_id = invoice['id']
				invoice_sent_email = self.env['account.move'].search(
					[('id', '=', invoice_id)])
				if invoice_sent_email:
					invoice_sent_email.write({'want_to_send_email': False,'email_sent':True})
		
		# for invoice in invoices_id:
		#     invoice_id = invoice['id']
		#     invoice = self.env['account.move'].browse(invoice_id)
		#
		#     template_id = self.env.ref('account.email_template_edi_invoice')
		#     template_id.send_mail(invoice.id, force_send=True)
		#     if invoice:
		#         invoice.write({'want_to_send_email': False})

	@api.depends('move_type', 'line_ids.amount_residual')
	def _compute_payments_widget_reconciled_info(self):
		super()._compute_payments_widget_reconciled_info()
		for move in self:
			payments_widget_vals = {'title': _('Less Payment'),
									'outstanding': False, 'content': []}

			if move.state == 'posted' and move.is_invoice(
					include_receipts=True):
				reconciled_vals = []
				reconciled_partials = (
					move._get_all_reconciled_invoice_partials())
				for reconciled_partial in reconciled_partials:
					counterpart_line = reconciled_partial['aml']
					if counterpart_line.move_id.ref:
						reconciliation_ref = '%s (%s)' % (
							counterpart_line.move_id.name,
							counterpart_line.move_id.ref)
					else:
						reconciliation_ref = counterpart_line.move_id.name
					if (counterpart_line.amount_currency and
							counterpart_line.currency_id !=
							counterpart_line.company_id.currency_id):
						foreign_currency = counterpart_line.currency_id
					else:
						foreign_currency = False
					card_number = []  # Initialize card_number
					card_ref = counterpart_line.payment_id.accept_blue_ref
					if card_ref:
						card_details = self.env['accept.blue.line'].search(
							[('pay_ref_no', '=', card_ref),('account_accept_move_id','=',move.id)])
						for card in card_details:
							card_number.append(card.credit_card_no_encr)
					reconciled_vals.append({
						'name': counterpart_line.name,
						'journal_name': counterpart_line.journal_id.name,
						'amount': reconciled_partial['amount'],
						'currency_id': move.company_id.currency_id.id if
						reconciled_partial['is_exchange'] else
						reconciled_partial['currency'].id,
						'date': counterpart_line.date,
						'partial_id': reconciled_partial['partial_id'],
						'account_payment_id': counterpart_line.payment_id.id,
						'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
						'move_id': counterpart_line.move_id.id,
						'ref': reconciliation_ref,
						# these are necessary for the views to change depending on the values
						'is_exchange': reconciled_partial['is_exchange'],
						'amount_company_currency': formatLang(self.env,
															  abs(counterpart_line.balance),
															  currency_obj=counterpart_line.company_id.currency_id),
						'amount_foreign_currency': foreign_currency and formatLang(
							self.env, abs(counterpart_line.amount_currency),
							currency_obj=foreign_currency),
						'card_number': card_number
					})
				payments_widget_vals['content'] = reconciled_vals

			if payments_widget_vals['content']:
				move.invoice_payments_widget = payments_widget_vals
			else:
				move.invoice_payments_widget = False

