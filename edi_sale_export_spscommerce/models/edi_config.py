import logging
import os
from lxml import etree as ET  # DOC : https://lxml.de/api/index.html

from odoo import api, fields, models, _


_logger = logging.getLogger(__name__)


class SyncDocumentType(models.Model):
    _inherit = 'sync.document.type'

    doc_code = fields.Selection(selection_add=[
        ('export_sale_acknowledgement_xml', '855 - Export Sale Acknowledgement')
    ], ondelete={'export_sale_acknowledgement_xml': 'cascade'})

    @api.model
    def _do_export_sale_acknowledgement_xml(self, conn, sync_action_id, values):
        '''
        Performs the document synchronization for the new document code
        @param conn : sftp/ftp connection class.
        @param sync_action_id: recordset of type `edi.sync.action`
        @param values:dict of values that may be useful to various methods

        @return bool : return bool (True|False)
        '''
        conn._connect()
        conn.cd(sync_action_id.dir_path)
        # Get sale orders to be sent to EDI:
        # Get individual records passed when SO hits action_confirm() -> values['records']
        # or get all pending records when user runs the synchronization action manually
        orders = values.get('records') or self.env['sale.order'].sudo().search(
            [('state', '=', 'sale'), ('edi_status', '=', 'pending')])

        for order in orders:
            edi_855 = self.generate_edi855(order)
            etree_edi_855 = ET.fromstring(edi_855)
            order_data = ET.ElementTree(etree_edi_855)
            ET.indent(order_data, space="  ")

            if order_data:
                filename = '855_sale_%s.xml' % order.name.replace('/', '_')
                with open(filename, 'wb') as file:
                    order_data.write(file, method="c14n")

                filename = filename.strip()
                try:
                    with open(filename, 'rb') as file:
                        conn.upload_file(filename, file)
                        file.close()
                    order.write(
                        {'edi_status': 'sent', 'edi_date': fields.Datetime.now()})
                    order.sudo().message_post(
                        body=_('Sale Order file created on the EDI server %s' % filename))
                    _logger.info('Sale Order file created on the server path of %s/%s' %
                                 (sync_action_id.dir_path, filename))
                except Exception as e:
                    order.write({'edi_status': 'fail'})
                    _logger.error('file not uploaded %s' % e)
                os.remove(filename)
            self.flush_model()
        conn._disconnect()
        return True

    def generate_edi855(self, order):
        """Generates the EDI 855 POA file for the given sale order"""
        if order.date_time_qualifier == '002':
            date = order.commitment_date
        elif order.date_time_qualifier == '118':
            date = order.requested_pickup_date
        else:
            date = order.additional_date
        if not date:
            date = fields.Datetime.now()
        values = {
            'partner_id': order.partner_id,
            'order': order,
            'date': date,
        }
        edi_855 = self.env['ir.qweb']._render(
            'edi_sale_export_spscommerce.edi_855', values=values)
        return edi_855
