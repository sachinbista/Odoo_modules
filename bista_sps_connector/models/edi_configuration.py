# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

import io
import paramiko
import fnmatch
import base64

from bs4 import BeautifulSoup

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class EDIConfig(models.Model):
    _name = "edi.config"
    _description = "EDI Configuration"
    _inherit = 'mail.thread'

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(string='Active', default=True,
                            tracking=True)
    # partner_id = fields.Many2one('res.partner', string="Customer", domain=[('parent_id', '=', False)], required=True,
    #                              tracking=True)
    edi_846 = fields.Boolean(string='EDI-846', default=False, readonly=False)
    edi_850 = fields.Boolean(
        string='EDI-850', default=False, tracking=True)
    edi_855 = fields.Boolean(
        string='EDI-855', default=False, tracking=True, readonly=False)
    edi_860 = fields.Boolean(string='EDI-860', default=False, tracking=True,
                             readonly=False)
    edi_865 = fields.Boolean(string='EDI-865', default=False, readonly=False)
    edi_856 = fields.Boolean(
        string='EDI-856', default=False, tracking=True)
    edi_810 = fields.Boolean(
        string='EDI-810', default=False, tracking=True)
    edi_811 = fields.Boolean(
        string='EDI-811', default=False, tracking=True, readonly=False)
    edi_inbound_file_path = fields.Char(
        string="Inbound File Path", tracking=True, default="/testout/")
    edi_outbound_file_path = fields.Char(
        string="Outbound File Path", tracking=True, default="/testin/")
    # edi_sales_rep = fields.Many2one('sales.rep', string="Sales Rep", tracking=True)
    # pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', tracking=True)
    partner_ids = fields.One2many(
        'res.partner', 'edi_config_id', string='Partner', readonly=True)
    ftp_username = fields.Char(string="SFTP Username")
    ftp_passwd = fields.Char(string="SFTP Password")
    hostname = fields.Char(string="Hostname", default='sftp.spscommerce.com')
    port_no = fields.Integer(string="TCP Port")
    company_id = fields.Many2one('res.company', string="Company")
    state = fields.Selection([
        ('draft', 'Draft'), ('success', 'Success'), ('fail', 'Fail')],
        string='Status', help='Connection status',
        default='draft', tracking=True)

    # s_order_type_id = fields.Many2one("sale.order.type", string="Order Type", tracking=True)
    # analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
    #                                       tracking=True)
    # name = fields.Char("Name", required=True)
    # delivery_file_path = fields.Char(string="Delivery File Path")
    # invoice_file_path = fields.Char(string="Invoice File Path")
    # import_order_path = fields.Char(string="Import Order Path")

    # _sql_constraints = [
    #     ('partner_id_unique', 'unique (partner_id)', 'You can create only one record for each partner!')]

    # @api.model
    # def create(self, vals):
    #     res = super(EDIConfig, self).create(vals)
    #
    #     partner_records = self.env['res.partner'].search([
    #         '|', ('id', '=', res.partner_id.id), ('id', 'child_of', [res.partner_id.id])
    #     ])
    #     if partner_records:
    #         res.update({'partner_ids': [(6, 0, partner_records.ids)]})
    #     return res

    # def write(self, vals):
    #     res = super(EDIConfig, self).write(vals)
    #     if vals.get('partner_id'):
    #         partner_rec = self.env['res.partner'].browse(vals.get('partner_id'))
    #         if partner_rec:
    #             partner_records = self.env['res.partner'].search([
    #                 '|', ('id', '=', partner_rec.id), ('id', 'child_of', [partner_rec.id])
    #             ])
    #             if partner_records:
    #                 self.update({'partner_ids': [(6, 0, partner_records.ids)]})
    #     return res

    def edi_action_archive(self):
        """
            Smart button action to archive or active an EDI config record.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        if self.active:
            self.update({'active': False})
        else:
            self.update({'active': True})

    def test_connection(self):
        """
            This function is used to build connection with the sftp server.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """

        sftp = ''
        transport = ''
        for rec in self:
            try:
                host = rec.hostname
                port = int(rec.port_no)
                transport = paramiko.Transport((host, port))
                password = rec.ftp_passwd
                username = rec.ftp_username
                transport.connect(username=username, password=password)

                sftp = paramiko.SFTPClient.from_transport(transport)
                self.update({'state': 'success'})

            except Exception as e:
                self.update({'state': 'fail'})
                self._cr.commit()
                raise UserError(_('Connection Failed - %s' % e))
        return sftp, transport

    def reset_to_draft(self):
        """
            Button action to reset to draft.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        self.update({'state': 'draft'})

    def import_edi_data_queue_job(self, filename, b_ncfile):
        try:
            decoded_bytes = base64.b64decode(b_ncfile)
            bs_data = BeautifulSoup(decoded_bytes, 'xml')
            data_queue_id = self.env['order.data.queue'].create(
                {'edi_order_data': bs_data, 'edi_config_id': self.id})
            if b_ncfile:
                attachments = self.env['ir.attachment'].create([
                    {'name': filename,
                     'datas': b_ncfile,
                     'res_model': 'order.data.queue',
                     'res_id': data_queue_id.id,
                     'type': 'binary',
                     }
                ])
        except Exception as e:
            raise ValidationError(_(str(e)))

    def import_edi_data(self, file_numbers=10):
        """
            This method is used to import the edi data from the inbound folder of sftp server to the Purchase Order Data Queue.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        for rec in self.search([('active', '=', True),
                                ('edi_850', '=', True),
                                ('state', '=', 'success')]):
            sftp, transport = rec.test_connection()
            localpath = rec.edi_inbound_file_path
            count = 0
            remove_source_path = []
            for filename in sftp.listdir(localpath):
                if count == file_numbers:
                    return
                count += 1
                source = ''
                b_ncfile = ''
                if fnmatch.fnmatch(filename, "*.xml") and filename.startswith('850'):
                    source = localpath + filename
                    ncfile = sftp.open(source)
                    ncfile.prefetch()
                    b_ncfile = ncfile.read()
                if not filename.endswith('.xml'):
                    continue
                if b_ncfile:
                    b_ncfile_base64 = base64.b64encode(b_ncfile).decode('utf-8')
                    rec.with_delay(description="Creating EDI 850 Order Data Queue Records",
                                   max_retries=5).import_edi_data_queue_job(filename, b_ncfile_base64)
                if source:
                    remove_source_path.append(source)
            for rem_sou in remove_source_path:
                sftp.remove(rem_sou)
            sftp.close()
            transport.close()

    def import_860_order_data_queue(self, file_count=10):
        """
        Define the function to process the files and create the queue.
        @param file_count:
        @type file_count:
        @return:
        @rtype:
        """
        for rec in self.search([('active', '=', True), ('edi_860', '=', True)]):
            sftp, transport = rec.test_connection()
            localpath = rec.edi_inbound_file_path
            count = 0
            for filename in sftp.listdir(localpath):
                if count == file_count:
                    return
                count += 1
                source = ''
                binary_file = ''
                if fnmatch.fnmatch(filename, "*.xml") and filename.startswith('860'):
                    source = localpath + filename
                    xml_file = sftp.open(source)
                    xml_file.prefetch()
                    binary_file = xml_file.read()
                if not filename.endswith('.xml'):
                    continue
                if binary_file:
                    binary_data = BeautifulSoup(binary_file, 'xml')
                    update_data_queue_id = self.env['order.data.update.queue'].create(
                        {'edi_order_data': binary_data, 'edi_config_id': rec.id})
                    if binary_file:
                        attachments = self.env['ir.attachment'].create([
                            {'name': filename,
                             'datas': base64.b64encode(binary_file),
                             'res_model': 'order.data.queue',
                             'res_id': update_data_queue_id.id,
                             'type': 'binary',
                             }
                        ])
                if source:
                    sftp.remove(source)
            sftp.close()
            transport.close()

    def export_edi_data(self, data_xml, file_path):
        """
        This method is used to export xml file in the sftp server folder
        file path.
        :return:
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """

        sftp, transport = self.test_connection()
        data_xml1 = io.StringIO(data_xml)
        sftp.putfo(data_xml1, file_path)

        sftp.close()
        transport.close()

    def export_all_data_queues(self):
        """
            This method is used in schedular to export the data from the respective data queues to the outbound
            file path of the sftp server.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        ack_order_data_queue = self.env['order.ack.data.queue'].search(
            [('state', '=', 'draft')])
        shipment_order_data_queue = self.env['shipment.data.queue'].search(
            [('state', '=', 'draft')])
        invoice_order_data_queue = self.env['invoice.data.queue'].search(
            [('state', '=', 'draft')])

        if ack_order_data_queue:
            ack_order_data_queue.export_data()
        if shipment_order_data_queue:
            shipment_order_data_queue.export_data()
        if invoice_order_data_queue:
            invoice_order_data_queue.export_data()

    def action_update_edi_queue_state(self):
        """
        Define the Cron function to update the failed status queues to draft.
        @return:
        @rtype:
        """
        import_queues = self.env['order.data.queue'].search(
            [('state', '=', 'fail')])
        update_queues = self.env["order.data.update.queue"].search(
            [('state', '=', 'fail')])
        if import_queues:
            import_queues.update({'state': 'draft'})
        if update_queues:
            update_queues.update({'state': 'draft'})
