# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, http
import json
from datetime import date, datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class GoFlowErrorLog(models.Model):
    _name = "goflow.error.log"
    _order = 'id desc'
    _description = "GoFlow Error Log"

    name = fields.Char('Name')
    message = fields.Text('Message')
    request = fields.Text('Request')
    request_type = fields.Selection([
        ('get', 'GET'), ('post', 'POST'),
        ('put', 'PUT'), ('delete', 'DELETE'),
        ('patch', 'PATCH')], 'Request Type')
    response = fields.Text('Response')
    status = fields.Text('status')
    user_id = fields.Many2one('res.users', 'Request User')
    partner_id = fields.Many2one('res.partner', 'Partner')
    api_headers = fields.Text('Headers')
    api_url = fields.Char('URL')
    request_payload = fields.Text('Request payload')
    response_data = fields.Text('API Response')


    @api.model
    def create(self, vals):
        res = super(GoFlowErrorLog, self).create(vals)
        company = self.env.company
        users_mail_list_str = ""
        for users in company.goflow_mail_user_ids:
            if users.partner_id.email:
                users_mail_list_str += users.partner_id.email + ","
        if res:
            subject = "Goflow API Request Failed"
            body_content = ""
            try:
                if res.message:
                    message = eval(res.message)
                    if message.get('message'):
                        body_content = message.get('message')
                    else:
                        body_content = message
                    if res.status in ['401','403','404','422','429','503']:
                        self.send_goflow_mail(body_content,subject,users_mail_list_str,res)
            except Exception as e:
                message = f"Error while convert error message: {str(e)}"
                _logger.info(message)
        return res

    def send_goflow_mail(self,body_content,subject,to_mail_str,log):
        company = self.env.company
        # url for btn
        action_id = self.env.ref('bista_go_flow.goflow_error_logs_action').id
        menu_id = self.env.ref('bista_go_flow.menu_goflow_error_log').id
        url = http.request.httprequest.host_url + "web#id=" + str(log.id) \
        + "&action=" + str(action_id) \
        + "&model=goflow.error.log&view_type=form&menu_id=" + str(menu_id)

        body=f"""Dear Sir/Madam,
        <br/>
        <h3>Goflow API Request has been Failed. Kindly check fail message below and view Log:</h3>
        <ul>
            <li><b>{body_content}</b></li>
        </ul>
        <a style="background-color:#875a7b;padding:10px;text-decoration:none;color:#fff;border-radius:5px" 
        href="{url}">View <span class="il">Log</span></a>
        <br/>
        <br/>
        Thanks,
        <br/>
        Team {company.name}
        """
        if to_mail_str:
            self.env['mail.mail'].sudo().create({
                'email_from': self.env.user.email_formatted,
                'author_id': self.env.user.partner_id.id,
                'body_html': body,
                'subject': subject ,
                'email_to': to_mail_str,
            }).send()

    def goflow_resync_api(self):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        if go_flow_instance_obj and self.request_type and self.request and self.request_payload:
            url = self.api_url.split("com")
            payload = eval(self.request_payload)
            response = go_flow_instance_obj._send_goflow_request(self.request_type, url[1],payload=payload)

    def go_flow_delete_log(self,days):
        rec_date = date.today()
        rec_date = rec_date - timedelta(days=days)
        query = f"""
            DELETE FROM goflow_error_log WHERE create_date < DATE('{str(rec_date)}');
        """
        self._cr.execute(query)