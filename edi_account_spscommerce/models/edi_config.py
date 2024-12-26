import logging
import os
from lxml import etree as ET # DOC : https://lxml.de/api/index.html

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SyncDocumentType(models.Model):

    _inherit = 'sync.document.type'

    doc_code = fields.Selection(selection_add=[
                                ('export_invoice_xml', '810 - Export Invoice (SPS Commerce XML)')],
                                ondelete = {'export_invoice_xml': 'cascade'})


    @api.model
    def _do_export_invoice_xml(self, conn, sync_action_id, values):
        '''
        Performs the document synchronization for the new document code
        @param conn : sftp/ftp connection class.
        @param sync_action_id: recordset of type `edi.sync.action`
        @param values:dict of values that may be useful to various methods

        @return bool : return bool (True|False)
        '''
        conn._connect()
        conn.cd(sync_action_id.dir_path)

        # Get sale invoices to be sent to edi:
        # Get individual records passed when SO hits action_post()
        # or get all pending records when user runs the synchronization action manually
        invoices = values.get('records') or self.env['account.move'].sudo().search([('state', '=', 'posted'),
                                                                                    ('edi_status', '=', 'pending'),
                                                                                    ('partner_id.outbound_edi_inv', '=', True)
                                                                                    ])
        invoices._check_edi_required_fields()

        for invoice in invoices:
            edi_810 = self.generate_edi810(invoice)
            etree_edi_810 = ET.fromstring(edi_810)
            invoice_data = ET.ElementTree(etree_edi_810)
            ET.indent(invoice_data, space="  ")

            if invoice_data:
                filename = '810_invoice_%s.xml' % (invoice.ref or invoice.name.replace('/', '_'))
                with open(filename, 'wb') as file:
                    invoice_data.write(file, method="c14n")
                try:
                    with open(filename, 'rb') as file:
                        conn.upload_file(filename, file)
                        file.close()
                    # Update EDI Status to sent
                    invoice.write({'edi_status': 'sent', 'edi_date': fields.Datetime.now()})
                    invoice.sudo().message_post(body=_('Invoice file created on the EDI server %s' % filename))
                    _logger.info('Invoice file created on the server path of %s/%s' % (sync_action_id.dir_path, filename))
                except Exception as e:
                    invoice.write({'edi_status': 'fail'})
                    _logger.error('file not uploaded %s' % e)
                os.remove(filename)
            self.flush_model()
        conn._disconnect()
        return True

    def generate_edi810(self, invoice):
        """Generates the EDI 810 file for the given invoice"""
        source_so = self.env['sale.order'].search([('name', '=', invoice.invoice_origin)], limit=1)
        if source_so.date_time_qualifier == '002':
            date = source_so.commitment_date
        elif source_so.date_time_qualifier == '118':
            date = source_so.requested_pickup_date
        else:
            date = source_so.additional_date
        if not date:
            date = fields.Datetime.now()
        values = {
            'partner' : invoice.partner_id,
            'invoice' : invoice,
            'lines': invoice.invoice_line_ids.filtered(lambda r: r.display_type not in ['line_section', 'line_note']),
            'date': date,
            'source_so': source_so,
            }
        edi_810 = self.env['ir.qweb']._render('edi_account_spscommerce.edi_810', values=values)
        return edi_810
