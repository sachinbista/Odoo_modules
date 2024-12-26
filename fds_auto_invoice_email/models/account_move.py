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

	# @api.model_create_multi
	# def create(self, vals_list):
	# 	res = super().create(vals_list)
	# 	if self.env.context.get('autosend_email'):
	# 		res.want_to_send_email = True
	# 	return res

	@api.model
	def send_invoice_reminders(self):
		current_company_id = self.env.user.company_id.id
		domain = [('company_id', '=', current_company_id),
		          ('move_type', '=', 'out_invoice'),
		          ('want_to_send_email', '=', True)]
		invoices_id = self.env['account.move'].search_read(domain, ['name','invoice_date','amount_total',
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
			email_body += "Please find below your outstanding invoices:<br><br>"
			email_body += """
			    <table border="1" style="border-collapse: collapse; width: 100%;">
			        <tr>
			            <th style="padding: 8px; text-align: left;">Invoice Number</th>
			            <th style="padding: 8px; text-align: left;">Invoice Date</th>
			            <th style="padding: 8px; text-align: left;">Amount</th>
			        </tr>
			"""
			attachment_list = []
			
			for invoice in customer_invoices:
				email_body += f"""
				                    <tr>
				                        <td style="padding: 8px;">{invoice['name']}</td>
				                        <td style="padding: 8px;">{invoice['invoice_date']}</td>
				                        <td style="padding: 8px;">{invoice['amount_total']}</td>
				                    </tr>
				                """
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
			
			# invoice_numbers = ", ".join(
			# 	invoice['name'] for invoice in customer_invoices)
			email_body += (f"Please remit payment at your earliest "
			               f"convenience.<br /><br />")
			email_body += ("Do not hesitate to contact us if you have any "
			               "questions.<br /><br />")
			email_body += ("If this invoice has not been received by its intended recipient,"
						   "please contact 4orders@premierprintsinc.com or call 662-840-4060 x222 to let us know."
			               "questions.")

			template_id = self.env.ref(
				'fds_auto_invoice_email.email_template_account_invoice').id
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