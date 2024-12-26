from odoo import models, fields, api
from datetime import date
import xlsxwriter
import base64
import pytz
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id_payment = fields.Many2one('sale.order', string="Sale Order Ref")
    warehouse_id = fields.Many2one(related="sale_order_id_payment.warehouse_id")

    @api.model_create_multi
    def create(self, vals_list):
        account_move_obj = self.env['account.move']
        for vals in vals_list:
            ref_value = vals.get('ref')
            if ref_value:
                move_id = account_move_obj.search([('name', 'like', ref_value)], limit=1)
                if move_id:
                    vals['sale_order_id_payment'] = move_id.sale_order_id.id
        return super(AccountPayment, self).create(vals_list)

    def send_payment_reminders_notification(self):
        user_ids = self.env.company.notify_user_ids
        today = date.today()
        today_date = date.today().strftime('%Y-%m-%d')
        file_name = 'Payments' + ' ' + today_date + '.xlsx'
        workbook = xlsxwriter.Workbook('/tmp/' + file_name)
        sheet = workbook.add_worksheet('FSL Inventory Report')
        # cdate = datetime.now().replace(tzinfo=pytz.utc). \
        #     astimezone(pytz.timezone(self.env.user.tz or 'UTC'))
        title_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'bg_color': '#B8B8B8',
            'align': 'center',
            'valign': 'vcenter'})
        sheet.set_column('A:C', 20)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:J', 20)
        bold = workbook.add_format({'bold': True})
        date_frmt = workbook.add_format({'align': 'right', 'bold': True})
        total_format = workbook.add_format({'border': 1, 'bold': True})
        rows = 0
        cols = 0

        # Report Column Headers
        headers = ['Created on', 'Warehouse', 'Sale Order Ref', 'Customer/Vendor',
                   'Name', 'Total', 'Last Modified on', 'Last Updated by', 'Status', 'Journal']
        cols = 0
        for header in headers:
            sheet.write(rows, cols, header, title_format)
            cols += 1
        rows += 1
        warehouse_lst = []
        location_lst = []
        payments = self.search([('date', '=', today),('company_id','=',self.env.company.id)])
        for payment in payments:
            sheet.write(rows, 0, payment.create_date.date().strftime('%Y-%m-%d') or'')
            sheet.write(rows, 1, payment.warehouse_id.name or  '')
            sheet.write(rows, 2, payment.sale_order_id_payment.name or '')
            sheet.write(rows, 3, payment.partner_id.name or False)
            sheet.write(rows, 4, payment.payment_method_name or '')
            sheet.write(rows, 5, payment.amount_total or '')
            sheet.write(rows, 6, payment.write_date.date().strftime('%Y-%m-%d') or '')
            sheet.write(rows, 7, payment.write_uid.name or '')
            sheet.write(rows, 8, payment.state or '')
            sheet.write(rows, 9, payment.journal_id.name or False)
            rows += 1
        workbook.close()
        fsl_file = base64.b64encode(open('/tmp/' +
                                         file_name, 'rb').read())
        email_body = (f"Hello,"
                      f"<br>Today Payment Received ")
        attachment_data = {
            'name': f"Today Payments.xlsx",
            'datas': fsl_file,
            'res_model': 'mail.compose.message',
            'type': 'binary',
        }

        attachment_id = self.env['ir.attachment'].sudo().create(
            attachment_data)

        template_id = self.env.ref(
            'bista_payments.email_template_account_payment_notification').id
        template = self.env['mail.template'].browse(template_id)
        for user in user_ids:
            print("dddddddddddddddd",user)
            template.send_mail(self.id,
                               force_send=True,
                               email_values={'email_to': user.email,
                                             'body_html': email_body,
                                             'attachment_ids': [
                                                 (6, 0, [attachment_id.id])]
                                             }
                               )

        return True
