# -*- coding: utf-8 -*-

import base64
import dateutil.utils
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class PosOrderReport(models.Model):
    _inherit = "pos.order"

    def sales_report_notify_users_mail(self):
        users_to_notify = self.env['ir.config_parameter'].sudo().get_param(
            'pos_customization.pos_report_notify_user_ids')
        attachment_list = []
        if users_to_notify:
            user_ids = [int(user_id) for user_id in users_to_notify.split(',')]
            users = self.env['res.users'].browse(user_ids)
            if not users:
                raise UserError(_("No valid users to notify."))
            report = self.env.ref('point_of_sale.sale_details_report')
            if not report:
                raise UserError(_("Sales details report not found."))
            if report:
                pdf_content, format = self.env[
                    'ir.actions.report'].sudo()._render_qweb_pdf(
                    report_ref=report)
                attachment = self.env['ir.attachment'].create({
                    'name': 'sales_report.pdf',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'mail.compose.message',
                    'type': 'binary',
                })
                attachment_list.append(attachment.id)
                for user in users:
                    template_id = self.env.ref('pos_customization.template_user_sales_report_notify_usersss').id
                    template = self.env['mail.template'].browse(template_id)
                    from_date = dateutil.utils.today()
                    to_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    email_body = f"""
                    Hello,
                    <br/>
                    From: {from_date}
                    <br/>
                    To: {to_date}
                    <br/>
                    Sales Details Report
                    """
                    template.send_mail(self.id,
                                       force_send=True,
                                       email_values={'email_to': user.email,
                                                     'body_html': email_body,
                                                     'attachment_ids': [
                                                         (6, 0, attachment_list)]}
                                       )
            return True