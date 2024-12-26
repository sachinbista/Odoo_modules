# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

import io
import paramiko
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BistaSftpConnection(models.Model):
    _name = 'bista.sftp.connection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Bista SFTP Connection'
    _rec_name = 'sftp_username'

    sftp_username = fields.Char(string="SFTP Username", required=True)
    sftp_passwd = fields.Char(string="SFTP Password")
    hostname = fields.Char(string="Hostname")
    port_no = fields.Integer(string="TCP Port")
    company_id = fields.Many2one('res.company', string="Company", required=True)
    sftp_file_path = fields.Char(string="SFTP File Path", required=True)
    customer_alias = fields.Boolean(string="Customer Alias", default=False)
    product_internal_ref = fields.Boolean(string="Product Internal Ref", default=False)
    customer_id = fields.Many2one('res.partner', string="Customer",domain="[('parent_id', '=', False)]")
    state = fields.Selection([
        ('draft', 'Draft'), ('success', 'Success'), ('fail', 'Fail')],
        string='Status', help='Connection status',
        default='draft')

    def test_connection(self):
        sftp = ''
        transport = ''
        for rec in self:
            try:
                host = rec.hostname
                port = int(rec.port_no)
                transport = paramiko.Transport((host, port))
                password = rec.sftp_passwd
                username = rec.sftp_username
                transport.connect(username=username, password=password)

                sftp = paramiko.SFTPClient.from_transport(transport)
                rec.write({'state': 'success'})

            except Exception as e:
                rec.write({'state': 'fail'})
                rec._cr.commit()
                raise UserError(_('Connection Failed - %s' % e))
        return sftp, transport

    def reset_to_draft(self):
        self.state = 'draft'

    @api.onchange('customer_alias')
    def onchange_customer(self):
        if not self.customer_alias:
            self.customer_id = False