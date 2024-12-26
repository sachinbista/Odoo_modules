import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

GS1_COMPANY_PREFIX = '0628820'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.constrains('carrier_tracking_ref')
    def set_bill_lading_number(self):
        for rec in self:
            if rec.bill_of_lading_number:
                continue
            rec.bill_of_lading_number = rec.carrier_tracking_ref
    
    edi_status = fields.Selection(selection=[
                                ('draft', 'Draft'),
                                ('pending', 'Pending'),
                                ('sent', 'Sent'),
                                ('fail', 'Failed')
                            ], string='EDI Status', default='draft', copy=False)

    edi_date = fields.Datetime(string='EDI Document Date')

    shipment_identification = fields.Char(string='EDI Shipment Identification')

    asn_number = fields.Char(string='ASN Number', help='Identification number assigned to the shipment by the shipper that uniquely identifies the shipment from origin to ultimate destination and is not subject to modification')

    asn_structure_code = fields.Char(string='ASN Structure Code', help='Code is the reflection of the structure of the document. For EDI purposes.', default='0001')

    all_contacts = fields.Text(string='Contacts',
                        help='Buyer and Receiving contacts transferred from the EDI')

    contact_name = fields.Char(string='Contact Name', help='Contact Name. Passed on to the EDI 856 Outbound file.')

    contact_phone = fields.Char(string='Contact Phone', help='Contact Phone Number. Passed on to the EDI 856 Outbound file.')

    carrier_trans_method_code = fields.Selection(selection=[
                                ('A', 'Air'),
                                ('C', 'Consolidation'),
                                ('M', 'Motor[Common Carrier]'),
                                ('P', 'Private Carrier'),
                                ('BU', 'Bus'),
                                ('E', 'Expedited Truck'),
                                ('H', 'Customer Pickup'),
                                ('L', 'Contract Carrier'),
                                ('R', 'Rail'),
                                ('O', 'Containerized Ocean'),
                                ('T', 'Best Way[Shippers Option]'),
                            ], string='Carrier Trans Method', default='M')

    carrier_alpha_code = fields.Char(string='Carrier Alpha Code',
                        help='4 digit SCAC code for applicable carrier (e.g. UPSN for UPS Ground)')

    carrier_routing = fields.Char(string='Carrier Routing',
                        help='Free-form description of the routing/requested routing for shipment or the originating carrier\'s identity')

    weight_edi = fields.Float(string='Weight (EDI)',
                        help='Weight of the shipment used on EDI')

    bill_of_lading_number = fields.Char(string='Bill Of Lading Number', required=False, help='A shipper assigned number that outlines the ownership, terms of carriage and is a receipt of goods')

    edi_backorder_origin = fields.Many2one(string='EDI Backorder Origin', related='sale_id.backorder_origin')


    @api.constrains('carrier_alpha_code')
    def _check_carrier_alpha_code(self):
        for record in self:
            if (record.partner_id.trading_partnerid) and (not record.carrier_alpha_code or len(record.carrier_alpha_code) != 4):
                raise ValidationError(_('Carrier Alpha Code should be 4 characters long.'))


    def generate_sscc_with_check_digit(self, sscc):
        odds_by_three = sum(int(sscc[i]) for i in range(len(sscc)) if i % 2 == 0) * 3
        evens = sum(int(sscc[i]) for i in range(len(sscc)) if i % 2 == 1)
        remainder = (odds_by_three + evens) % 10
        check_digit = (10 - remainder) % 10
        sscc_complete = sscc + str(check_digit)
        _logger.info('SSCC-18 generated: %s' % sscc_complete)
        return sscc_complete


    def generate_sscc(self, pallet):
        """
        The SSCC-18 ID is an 18 digit number used in the shipping label pallet that uniquely identifies the pallet.
        It is constructed by concatenating the following:
            '00' - Application Identifier
            '0' - Extension digit
            GS1 Company Prefix - 7 digits
            Pallet Number - 9 digits
            Check digit - 1 digit
        """

        pallet_number = ''.join(e for e in pallet if
                                e.isdigit())  # Filter out alphabetical characters and take only the numerical digits
        pallet_number = pallet_number.rjust(9, '0')  # Right-justify number i.e. pad with zeroes to the left
        sscc_without_check_digit = '0' + GS1_COMPANY_PREFIX + pallet_number
        return '00%s' % self.generate_sscc_with_check_digit(sscc_without_check_digit)


    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.sale_id:
                if not record.all_contacts and record.sale_id.all_contacts:
                    record['all_contacts'] = record.sale_id.all_contacts
                if not record.carrier_trans_method_code and record.sale_id.carrier_trans_method_code:
                    record['carrier_trans_method_code'] = record.sale_id.carrier_trans_method_code
                if not record.carrier_routing and record.sale_id.carrier_routing:
                    record['carrier_routing'] = record.sale_id.carrier_routing

            all_pickings = self.env['stock.picking'].sudo().search([('origin', '=', record.origin)])
            if 'bill_of_lading_number' in vals and vals['bill_of_lading_number'] != record.bill_of_lading_number:
                all_pickings.write({'bill_of_lading_number': vals['bill_of_lading_number']})
            if 'carrier_alpha_code' in vals and vals['carrier_alpha_code'] != record.carrier_alpha_code:
                all_pickings.write({'carrier_alpha_code': vals['carrier_alpha_code']})
            if 'carrier_routing' in vals and vals['carrier_routing'] != record.carrier_routing:
                all_pickings.write({'carrier_routing': vals['carrier_routing']})
            if 'carrier_trans_method_code' in vals and vals['carrier_trans_method_code'] != record.carrier_trans_method_code:
                all_pickings.write({'carrier_trans_method_code': vals['carrier_trans_method_code']})
            if 'weight_edi' in vals and vals['weight_edi'] != record.weight_edi:
                all_pickings.write({'weight_edi': vals['weight_edi']})
            if 'contact_name' in vals and vals['contact_name'] != record.contact_name:
                all_pickings.write({'contact_name': vals['contact_name']})
            if 'contact_phone' in vals and vals['contact_phone'] != record.contact_phone:
                all_pickings.write({'contact_phone': vals['contact_phone']})
        return res


    def _check_required_fields(self):
        if not self.bill_of_lading_number or not self.carrier_trans_method_code or not self.carrier_alpha_code:
            raise ValidationError('Bill Of Landing Number, Carrier Trans Method, and Carrier Alpha Code are mandatory fields.')

        # Check for pallets in each line
        for line in self.move_line_ids_without_package:
            if not line.result_package_id:
                raise ValidationError('All lines must have a Destination Package assigned to create the ASN file.')
            if not line.product_uom_id:
                raise ValidationError('All lines must have an EDI UoM assigned to create the ASN file.')


    def _action_done(self):
        for picking in self:

            needs_edi_asn = False
            # Only selected partners with output deliveries that come from a sale order need ASN
            if (picking.partner_id.outbound_edi_asn or picking.partner_id.parent_id.outbound_edi_asn) \
                    and picking.picking_type_id.sequence_code == 'OUT' \
                    and picking.origin:
                needs_edi_asn = True
                picking._check_required_fields()

            res = super(StockPicking, self)._action_done()

            if needs_edi_asn:
                base_edi = picking.env['edi.sync.action']
                sync_action = base_edi.search([('doc_type_id.doc_code', '=', 'export_shipping_xml')])
                if sync_action:
                    base_edi._do_doc_sync_cron(sync_action_id=sync_action, records=picking)
            return res
