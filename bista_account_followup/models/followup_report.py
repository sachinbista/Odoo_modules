from odoo import models, fields, api, _
import io
import base64
from odoo.tools.misc import xlsxwriter
from odoo.tools.misc import format_date, get_lang, formatLang


class ResPartner(models.Model):
    _inherit = "res.partner"

    def customer_statement_excel_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Customer Statement")
        worksheet.merge_range(0, 0, 0, 1, "Pending Invoices", workbook.add_format(
            {'bold': True, 'font_size': 13}))
        worksheet.write(0, 4, self.name)
        worksheet.write(1, 4, self.street or "")
        address_line = ""
        if self.city:
            address_line += self.city
        if self.state_id:
            address_line += " " + self.state_id.code
        if self.zip:
            address_line += " " + str(self.zip)
        worksheet.write(2, 4, address_line)
        if self.country_id:
            worksheet.write(3, 4, self.country_id.name or "")

        headers = ["Reference", "Date", "Due Date", "origin", "Communication", "Total Due"]
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'left'})
        for col, header in enumerate(headers):
            worksheet.write(6, col, header,workbook.add_format({'bold': True}))
            worksheet.set_column(6,col, 15)

        options = {"partner_id": self.id}
        data = self.env['account.followup.report']._get_followup_report_lines(options)

        for row, line in enumerate(data, start=7):

            worksheet.write(row, 0, line.get('name') or "")
            for col, column in enumerate(line['columns'], start=1):
                worksheet.write(row,col,column.get('name',""))

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        filename = f"{'Follow-up ' + self.name}.xlsx"
        output.close()

        if self._context.get("send_attachment"):
            attachment_vals = {
                'name': filename,
                'type': 'binary',
                'datas': file_data,
                'res_model': 'res.partner',  # Model to which the attachment is linked
                'res_id': self.id,  # Record ID of the linked model
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            }
            attachment = self.env['ir.attachment'].create(attachment_vals)
            return attachment

        return file_data, filename

    def _generate_pdf_report(self, options):
        partner = self
        action = self.env.ref('account_followup.action_report_followup')
        tz_date_str = format_date(self.env, fields.Date.today(),
                                  lang_code=self.env.user.lang or get_lang(self.env).code)
        # to avoid having dots in the name of the file.
        tz_date_str = tz_date_str.replace('.', '-')
        followup_letter_name = _("Follow-up %s - %s", partner.display_name, tz_date_str)
        followup_letter = action.with_context(lang=partner.lang or self.env.user.lang)._render_qweb_pdf(
            'account_followup.report_followup_print_all', partner.id, data={'options': options or {}})[0]
        attachment = self.env['ir.attachment'].create({
            'name': followup_letter_name,
            'raw': followup_letter,
            'res_id': partner.id,
            'res_model': 'res.partner',
            'type': 'binary',
            'mimetype': 'application/pdf',
        })
        return attachment

    # def send_followup_email(self, options):
    #     """
    #     Send a follow-up report by email to customers in self
    #     """
    #     for record in self:
    #         options['partner_id'] = record.id
    #
    #         # data = self.env['account.followup.report']._get_followup_report_lines(options)
    #         attachment = self.with_context(send_attachment=True).customer_statement_excel_report()
    #         pdf_attachment = self._generate_pdf_report(options)
    #         if pdf_attachment:
    #             options['attachment_ids'].append(pdf_attachment.id)
    #             options.update({'pdf_attachment': pdf_attachment.id})
    #         if attachment:
    #             options['attachment_ids'].append(attachment.id)
    #         self.env['account.followup.report']._send_email(options)

    def execute_followup(self, options):
        """ Execute the actions to do with follow-ups for this partner.
        This is called when processing the follow-ups manually, via the wizard.

        options is a dictionary containing at least the following information:
            - 'partner_id': id of partner (self)
            - 'email': boolean to trigger the sending of email or not
            - 'email_subject': subject of email
            - 'followup_contacts': partners (contacts) to send the followup to
            - 'body': email body
            - 'attachment_ids': invoice attachments to join to email/letter
            - 'sms': boolean to trigger the sending of sms or not
            - 'sms_body': sms body
            - 'print': boolean to trigger the printing of pdf letter or not
            - 'manual_followup': boolean to indicate whether this followup is triggered via the manual reminder wizard
        """
        self.ensure_one()
        if options.get("email"):
            pdf_attachment = self._generate_pdf_report(options)
            if pdf_attachment:
                options['attachment_ids'].append(pdf_attachment.id)
                options.update({'pdf_attachment': pdf_attachment.id})
            attachment = self.with_context(send_attachment=True).customer_statement_excel_report()
            if attachment:
                options['attachment_ids'].append(attachment.id)
        to_print = self._execute_followup_partner(options=options)
        if options.get('print') and to_print:
            return self.env['account.followup.report']._print_followup_letter(self, options)