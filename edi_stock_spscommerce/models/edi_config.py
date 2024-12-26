import os
import logging
import pytz
from lxml import etree as ET # DOC : https://lxml.de/api/index.html
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SyncDocumentType(models.Model):

    _inherit = 'sync.document.type'

    doc_code = fields.Selection(selection_add=[
                                ('export_shipping_xml', '856 - Export Shipping Acknowledgement (SPS Commerce XML)'),
                                ('import_shipping_xml', '945 - Import Warehouse Shipping Advice (SPS Commerce XML)')],
                                ondelete={'export_shipping_xml': 'cascade',
                                          'import_shipping_xml': 'cascade'})


    @api.model
    def _do_export_shipping_xml(self, conn, sync_action_id, values):
        '''
        Performs the document synchronization for the new document code
        @param conn : sftp/ftp connection class.
        @param sync_action_id: recordset of type `edi.sync.action`
        @param values:dict of values that may be useful to various methods
        @return bool : return bool (True|False)
        '''
        conn._connect()
        conn.cd(sync_action_id.dir_path)

        # Get shipments to be sent to edi:
        # Get individual records passed when SO hits button_validate()
        # or get all pending records when user runs the synchronization action manually
        pickings = values.get('records') or self.env['stock.picking'].sudo().search([('edi_status', '=', 'pending'), ('state', '=', 'done')])

        for picking in pickings:
            #picking_data = self.make_picking_xml_data(picking)
            edi_856 = self.generate_edi856(picking)
            etree_edi_856 = ET.fromstring(edi_856)
            picking_data = ET.ElementTree(etree_edi_856)
            ET.indent(picking_data, space="  ")
            #picking_data = ET.ElementTree(picking_data)

            if picking_data:
                filename = '856_shipment_%s.xml' % picking.name.replace('/', '_')
                with open(filename, 'wb') as file:
                    picking_data.write(file, method="c14n")

                filename = filename.strip()
                try:
                    with open(filename, 'rb') as file:
                        conn.upload_file(filename, file)
                        file.close()
                    # Update EDI Status to sent
                    picking.write({'edi_status': 'sent', 'edi_date': fields.Datetime.now()})
                    picking.sudo().message_post(body=_('Shipping file created on the EDI server %s' % filename))
                    _logger.info('Shipping file created on the server path of %s/%s' % (sync_action_id.dir_path, filename))
                except Exception as e:
                    picking.write({'edi_status': 'fail'})
                    _logger.error("file not uploaded %s" % e)
                os.remove(filename)
            self.flush_model()
        conn._disconnect()
        return True

    def generate_edi856(self, picking):
        """Generates the EDI 856 file for delivery order"""
        for line in picking.move_line_ids_without_package:
            if not line.result_package_id:
                raise ValidationError("Please assign a package to each line.")
        source_so = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
        partner = source_so.partner_id or picking.partner_id or ''
        tz = self.env.user.tz or pytz.utc
        timezone = pytz.timezone(tz)
        values = {
            'picking' : picking,
            'source_so' : source_so,
            'partner' : partner,
            'timezone' : timezone,
            }
        edi_856 = self.env['ir.qweb']._render('edi_stock_spscommerce.edi_856', values=values)
        return edi_856
