import logging
import pprint
import pytz

from datetime import datetime
from lxml import etree as ET  # DOC : https://lxml.de/api/index.html

from odoo.exceptions import ValidationError
from odoo import fields, models, _

EDI_DATE_FORMAT = '%Y-%m-%d'

_logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=4)

ns = {'sps': 'http://www.spscommerce.com/RSX'}


class SyncDocumentType(models.Model):
    _inherit = 'sync.document.type'

    doc_code = fields.Selection(selection_add=[
        ('import_so_xml', '850 - Import Order (SPS Commerce XML)')
    ], ondelete={'import_so_xml': 'cascade'})

    def _is_new_order(self, orderheader, PO_number):
        """
        Returns True if the order is not a duplicate.
        First, it checks if the import claims to be a new order.
        Then, it checks if an order with the same PO number already exists in db
        """

        tset_purpose_code = self.get_ele_text(orderheader, 'TsetPurposeCode')
        primary_PO_type_code = self.get_ele_text(orderheader, 'PrimaryPOTypeCode')

        if tset_purpose_code == '00' or primary_PO_type_code in ['SA', 'NE']:
            if self.env['sale.order'].search([('po_number', '=', PO_number)]):
                return False

        return True

    def get_uom(self, order_id, uom_edi):
        """
        Choose a Unit of Measure based on the OrderQtyUOM provided in the EDI file.
        EA stands for Units and CA stands for cases
        """

        uom = self.env['uom.uom'].search([('edi_code', '=', uom_edi)])

        if not uom:
            if uom_edi not in ['EA', 'CA']:
                self.env['sale.order.line'].create({
                    'order_id': order_id,
                    'name': 'UoM of %s not found. Units automatically assigned.' % uom_edi,
                    'display_type': 'line_note'
                })
            uom = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
            if not uom:
                raise ValidationError('Could not assign UoM. No unit named Units.')

        return uom

    def get_charges_allowances(self, chrg_allw_block):
        """Return a Charge/Allowance record or create one if a match is not found in the database"""

        data = {
            'indicator': self.get_ele_text(chrg_allw_block, 'AllowChrgIndicator'),
            'code': self.get_ele_text(chrg_allw_block, 'AllowChrgCode'),
            'amount': self.get_ele_text(chrg_allw_block, 'AllowChrgAmt'),
            'percent_qualifier': self.get_ele_text(chrg_allw_block, 'AllowChrgPercentQual'),
            'percent': self.get_ele_text(chrg_allw_block, 'AllowChrgPercent'),
            'handling_code': self.get_ele_text(chrg_allw_block, 'AllowChrgHandlingCode'),
        }

        charge_allow = self.env['charge.allowance'].search([
            ('indicator', '=', data['indicator']),
            ('code', '=', data['code']),
            ('amount', '=', data['amount']),
            ('percent_qualifier', '=', data['percent_qualifier']),
            ('percent', '=', data['percent']),
            ('handling_code', '=', data['handling_code']),
        ])

        if not charge_allow:
            charge_allow = self.env['charge.allowance'].create(data)

        return charge_allow

    def get_payment_terms(self, payment_terms, FOB_related_instruction=None):
        """
        Retrieves the corresponding payment term record from the database and
        returns the text contents for customer_payment_terms Text field. First tries to find a match by looking at the
        Terms Description field. If not found, it uses a "smarter" approach by looking at the rest of the fields.
        """
        terms_type = self.get_ele_text(payment_terms, 'TermsType')
        basis_date_code = self.get_ele_text(payment_terms, 'TermsBasisDateCode')
        discount_percentage = self.get_ele_text(payment_terms, 'TermsDiscountPercentage')
        discount_date = self.get_ele_text(payment_terms, 'TermsDiscountDate')
        discount_due_days = self.get_ele_text(payment_terms, 'TermsDiscountDueDays')
        net_due_date = self.get_ele_text(payment_terms, 'TermsNetDueDate')
        net_due_days = self.get_ele_text(payment_terms, 'TermsNetDueDays')
        terms_description = self.get_ele_text(payment_terms, 'TermsDescription')

        payment_term_id = self.env['account.payment.term'].search([('description', '=', terms_description)], limit=1)

        if not payment_term_id:
            # Immediate Payment
            if terms_type == '10':
                payment_term_id = self.env['account.payment.term'].search([]) \
                    .filtered(lambda p: p.line_ids.filtered(lambda line: line.value == 'balance' and line.days == 0))

            elif discount_percentage:
                # Retrieve the Odoo payment term record which lines match the EDI discount and the days
                payment_term_id = self.env['account.payment.term'].search([]) \
                    .filtered(
                    lambda p: p.line_ids.filtered(
                        lambda line: line.value == 'percent' and line.days == int(discount_due_days)) and p.line_ids.filtered(
                        lambda line: line.value == 'balance' and line.days == int(net_due_days or discount_due_days)))
            elif net_due_days:
                payment_term_id = self.env['account.payment.term'].search([]) \
                    .filtered(
                    lambda p: not p.line_ids.filtered(lambda line: line.value == 'percent') and p.line_ids.filtered(
                        lambda line: line.value == 'balance' and line.days == int(net_due_days)))

        customer_payment_terms = \
            'Terms Type: %s\nBasis Date Code: %s\nDiscount Percentage: %s\nDiscount Date: %s\nDiscount Due Days: %s\nNet Due Date: %s\nNet Due Days: %s\nTerms Description: %s\n' \
            % (terms_type, basis_date_code, discount_percentage, discount_date, discount_due_days, net_due_date,
               net_due_days, terms_description)

        if FOB_related_instruction is not None:
            FOB_pay_code = self.get_ele_text(FOB_related_instruction, 'FOBPayCode')
            FOB_location_qualifier = self.get_ele_text(FOB_related_instruction, 'FOBLocationQualifier')
            FOB_location_description = self.get_ele_text(FOB_related_instruction, 'FOBLocationDescription')

            customer_payment_terms += \
                'FOB Pay Code: %s\nFOB Location Qualifier: %s\nFOB Location Description: %s\n' \
                % (FOB_pay_code, FOB_location_qualifier, FOB_location_description)

        return customer_payment_terms, payment_term_id


    def prepared_sale_order_line_from_xml(self, line, order_id, partner, is_backorder=False):

        order_line = line.find('sps:OrderLine', ns)
        product_or_item_description = line.find('sps:ProductOrItemDescription', ns)
        physical_details = line.find('sps:PhysicalDetails', ns)
        line_sequence_number = self.get_ele_text(order_line, 'LineSequenceNumber')
        buyer_partnumber = self.get_ele_text(order_line, 'BuyerPartNumber')
        vendor_partnumber = self.get_ele_text(order_line, 'VendorPartNumber')
        barcode = self.get_ele_text(order_line, 'ConsumerPackageCode')  # The UPC is always passed in 'ConsumerPackageCode'
        consumer_package_code = self.get_ele_text(order_line, 'ConsumerPackageCode')
        ean = self.get_ele_text(order_line, 'EAN')
        gtin = self.get_ele_text(order_line, 'GTIN')
        product_id = order_line.find('sps:ProductID', ns)
        part_number = self.get_ele_text(product_id, 'PartNumber')
        name = self.get_ele_text(product_or_item_description, 'ProductDescription')

        Product = self.env['product.product']

        # If edi_code is not provided, choose 'Units' by default
        uom_edi = self.get_ele_text(order_line, 'OrderQtyUOM') or 'EA'
        uom = self.get_uom(order_id, uom_edi)

        pack_size = self.get_ele_text(physical_details, 'PackValue')

        has_different_ref_barcode = False
        product = Product.search([('default_code', 'ilike', vendor_partnumber), ('company_id', 'in', (False, self.env['sale.order'].browse(order_id).company_id.id))], limit=1)
        has_different_ref_barcode = True if product and product.barcode != barcode else False
        if not product:
            product = Product.search([('barcode', '=', barcode)], limit=1)
            has_different_ref_barcode = True if product and product.default_code != vendor_partnumber else False
        if not product:  # For variants, strip the leading and trailing characters
            product = Product.search([('barcode', '=', barcode[1:])], limit=1)
            has_different_ref_barcode = True if product and product.default_code != vendor_partnumber else False
        if not product:  # For Case UPC, strip the leading and trailing characters
            product = Product.search([('barcode', '=', barcode[1:-1])], limit=1)
            has_different_ref_barcode = True if product and product.default_code != vendor_partnumber else False

        if not product:
            _logger.info('Product Not found FROM the EDI - Barcode: %s' % barcode)
            # Create a note with the UPC number coming from EDI, Sales Price of the Product, Unit of Measure and the Quantity.
            line_data = {
                'order_id': order_id,
                'name': 'PRODUCT NOT FOUND - UPC/barcode: %s, EAN: %s, GTIN: %s, PART NUMBER %s, Price: %s, UoM: %s, Quantity: %s, LineSequence#: %s' % (
                    barcode, ean, gtin, vendor_partnumber, self.get_ele_text(order_line, 'PurchasePrice'), uom_edi,
                    self.get_ele_text(order_line, 'OrderQty'), line_sequence_number),
                'display_type': 'line_note',
                'price_unit': 0,
                'product_uom_qty': 0,
                'product_uom': False,
                'product_id': False,
                'customer_lead': 0,
                'has_different_ref_barcode': has_different_ref_barcode
            }
            return line_data

        product.sudo().write({'gtin': gtin})
        product.sudo().write({'ean': ean})

        # Charges Allowances on Line Level
        charges_allowances = line.find('sps:ChargesAllowances', ns)
        charges_allowances_text = ''
        if charges_allowances:
            allow_chrg_indicator = self.get_ele_text(charges_allowances, 'AllowChrgIndicator')
            allow_chrg_code = self.get_ele_text(charges_allowances, 'AllowChrgCode')
            reference_identification = self.get_ele_text(charges_allowances, 'ReferenceIdentification')
            charges_allowances_text = '%s\n%s\n%s\n\n' % (
                allow_chrg_indicator, allow_chrg_code, reference_identification)

        package = None
        quantity = int(self.get_ele_text(order_line, 'OrderQty'))
        if uom_edi == 'CA' and product.packaging_ids:
            package = product.packaging_ids.sorted(key=lambda r: r.create_date, reverse=True)[0]
            if package.qty:
                quantity *= package.qty

        order_in_cases = package and package.qty and uom_edi == 'CA'
        edi_price = float(self.get_ele_text(order_line, 'PurchasePrice')) or 0
        price_pricelist = edi_price
        # price_pricelist = self.env['sale.order'].get_gross_selling_price(partner, product, package)
        # if price_pricelist != edi_price:
        #     self.env['sale.order.line'].create({
        #         'order_id': order_id,
        #         'name': 'WARNING: Price mismatch between Odoo and EDI - Product: %s, Package: %s, EDI Price: %s, Selling Price: %s' % (
        #             product.name, package.name if package else 'None', edi_price, price_pricelist),
        #         'display_type': 'line_note'
        #     })

        # EDI price will be the price per case whenever the partner orders in Cases
        if order_in_cases and not partner.price_in_cases:
            edi_price *= package.qty

        if order_in_cases:
            if partner.price_in_cases:
                case_price = price_pricelist
                price_unit = price_pricelist / package.qty
            else:
                case_price = price_pricelist * package.qty
                price_unit = price_pricelist
        else:
            case_price = price_unit = price_pricelist

        # Get payment terms
        payment_terms = line.find('sps:PaymentTerms', ns)
        customer_payment_terms = ''
        payment_term_id = None
        if payment_terms is not None:
            customer_payment_terms, payment_term_id = self.get_payment_terms(payment_terms)

        # Taxes
        taxes = line.find('sps:Taxes', ns)
        if taxes:
            tax_code = self.get_ele_text(taxes, 'TaxTypeCode') or ''
            tax_percent = self.get_ele_text(taxes, 'TaxPercent') or ''
            tax_id_edi = self.get_ele_text(taxes, 'TaxID') or ''

        item_status_code = 'IA'
        if case_price != edi_price:
            item_status_code = 'IP'
        if is_backorder:
            item_status_code = 'IB'

        line_data = {
            'order_id': order_id,
            'product_id': product.id,
            'name': name or product.name,
            'product_uom_qty': quantity or 1,
            'product_uom': uom.id,
            'price_unit': price_unit,
            'case_price': case_price,
            'edi_price': edi_price,
            'display_type': '',
            'pack_size': pack_size or 1,
            'consumer_package_code': consumer_package_code,
            'line_sequence_number': line_sequence_number,
            'part_number': part_number,
            'vendor_part_number': vendor_partnumber,
            'buyer_part_number': buyer_partnumber,
            'product_packaging_id': package.id if package else None,
            'charges_allowances': charges_allowances_text,
            'payment_terms': customer_payment_terms,
            'tax_code': tax_code if taxes else 'TX',
            'tax_percent': tax_percent if taxes else '0',
            'tax_id_edi': tax_id_edi if taxes else '0',
            'item_status_code': item_status_code,
            'has_different_ref_barcode': has_different_ref_barcode
        }
        return line_data

    def get_ele_text(self, elemt, node_name):
        if elemt is None:
            return ''
        ele_node = elemt.find('sps:%s' % (node_name), ns)
        vals = str(ele_node.text) if ele_node is not None and ele_node.text is not None else ''
        _logger.info('read: `%s`: `%s`' % (node_name, vals))
        return vals[0] if len(vals) == 1 else vals

    def _add_contact_to_list(self, all_contacts_list, contact):
        code = self.get_ele_text(contact, 'ContactTypeCode') or ''
        contact_code = 'Buyer Contact' if code == 'BD' else 'Receiving Contact'
        contact_name = self.get_ele_text(contact, 'ContactName') or ''
        contact_phone = self.get_ele_text(contact, 'PrimaryPhone') or ''
        contact_tuple = (contact_code, contact_name, contact_phone)
        if contact_tuple not in all_contacts_list:
            all_contacts_list.append(contact_tuple)

    def _add_address_to_list(self, addresses, address):
        addresses += 'AddressName: %s\nAddressTypeCode: %s\nLocationCodeQualifier: %s\nAddressLocationNumber: %s\nStreet1: %s\nStreet2: %s\nCity: %s\nPostalCode: %s\nCountry: %s\n\n' % (
            self.get_ele_text(address, 'AddressName') or '',
            self.get_ele_text(address, 'AddressTypeCode') or '',
            self.get_ele_text(address, 'LocationCodeQualifier') or '',
            self.get_ele_text(address, 'AddressLocationNumber') or '',
            self.get_ele_text(address, 'Address1') or '',
            self.get_ele_text(address, 'Address2') or '',
            self.get_ele_text(address, 'City') or '',
            self.get_ele_text(address, 'PostalCode') or '',
            self.get_ele_text(address, 'Country') or '')


    def get_contacts(self, contacts, addresses, trading_partnerid):
        """
        Returns the following contact records to be assigned to the sale order:
        Customer (partner_id)
        Shipping Address (partner_shipping_id)
        Invoice Address (partner_invoice_id)
        Addresses (addresses)
        Contacts (all_contacts)

        @param contacts: Contacts at Header level
        """
        all_contacts = addresses = ''
        all_contacts_list = []

        for contact in contacts:
            self._add_contact_to_list(all_contacts_list, contact)

        main_partner = self.env['res.partner'].sudo().search([('trading_partnerid', '=', trading_partnerid),
                                                              ('is_company', '=', True)],
                                                             limit=1)
        partner_shipping_id = partner_invoice_id = ''
        for address in addresses:
            self._add_address_to_list(addresses, address)

            contact = address.find('sps:Contacts', ns) or None
            if contact:
                self._add_contact_to_list(all_contacts_list, contact)

            address_id = self.env['res.partner'].search(
                [('address_location_number', '=', self.get_ele_text(address, 'AddressLocationNumber'))], limit=1)

            address_type = self.get_ele_text(address, 'AddressTypeCode')
            contact_type = 'delivery' if address_type == 'ST' else 'invoice' #if address_type == 'BT' else 'contact'

            if not address_id and contact_type in ['delivery', 'invoice']:
                country = self.env['res.country'].search([('code', '=', self.get_ele_text(address, 'Country')[:2])],
                                                         limit=1)
                state = self.env['res.country.state'].search(
                    [('code', '=', self.get_ele_text(address, 'State')), ('country_id', '=', country.id)], limit=1)
                partner_data = {
                    'name': self.get_ele_text(address, 'AddressName'),
                    'parent_id': main_partner.id,
                    'trading_partnerid': trading_partnerid,
                    'location_code_qualifier': self.get_ele_text(address, 'LocationCodeQualifier'),
                    'address_location_number': self.get_ele_text(address, 'AddressLocationNumber'),
                    'country_id': country.id,
                    'state_id': state.id,
                    'street': self.get_ele_text(address, 'Address1'),
                    'street2': self.get_ele_text(address, 'Address2'),
                    'city': self.get_ele_text(address, 'City'),
                    'zip': self.get_ele_text(address, 'PostalCode'),
                    'type': contact_type,
                }
                address_id = self.env['res.partner'].create(partner_data)

            if contact_type == 'delivery':
                partner_shipping_id = address_id

            if contact_type == 'invoice':
                partner_invoice_id = address_id

        # Convert list of contacts to multiline text field
        for contact in all_contacts_list:
            all_contacts += 'Type: %s\nName: %s\nPhone: %s\n\n' % (contact[0], contact[1], contact[2])

        partner_shipping_id = partner_shipping_id or main_partner
        partner_invoice_id = partner_invoice_id or main_partner

        return main_partner, partner_shipping_id, partner_invoice_id, addresses, all_contacts

    def convert_TZ_UTC(self, TZ_datetime, is_datetime=False):
        """Convert datetime from user timezone to UTZ"""
        tz = pytz.timezone(self.env.user.tz or pytz.utc)
        format = "%Y-%m-%d %H:%M:%S"
        local_datetime_format = "%Y-%m-%d"
        now_utc = datetime.utcnow()  # Current time in UTC
        now_timezone = now_utc.astimezone(tz)  # Convert to current user time zone
        UTC_OFFSET_TIMEDELTA = datetime.strptime(now_utc.strftime(format), format) - datetime.strptime(now_timezone.strftime(format), format)
        if is_datetime:
            local_datetime_format = format
        local_datetime = datetime.strptime(TZ_datetime, local_datetime_format)
        result_utc_datetime = local_datetime + UTC_OFFSET_TIMEDELTA
        return result_utc_datetime.strftime(format)


    def prepared_order_from_xml(self, order):
        header = order.find('sps:Header', ns)
        summary = order.find('sps:Summary', ns)

        # OrderHeader data
        orderheader = header.find('sps:OrderHeader', ns)
        trading_partnerid = self.get_ele_text(orderheader, 'TradingPartnerId')
        po_number = self.get_ele_text(orderheader, 'PurchaseOrderNumber')
        tset_purpose_code = self.get_ele_text(orderheader, 'TsetPurposeCode')
        primary_PO_type_code = self.get_ele_text(orderheader, 'PrimaryPOTypeCode')
        vendor = self.get_ele_text(orderheader, 'Vendor')
        department = self.get_ele_text(orderheader, 'Department')

        # Check if current order is backorder
        backorder_origin = self.env['sale.order'].sudo().search(
            [('po_number', '=', po_number), ('backorder_origin', '=', None)], limit=1)

        # Order date - Converted to UTC
        date_order = self.get_ele_text(orderheader, 'PurchaseOrderDate')
        date_order = self.convert_TZ_UTC(date_order)

        # Get contacts
        contacts = header.findall('sps:Contacts', ns)
        addresses = header.findall('sps:Address', ns)
        partner, partner_shipping_id, partner_invoice_id, addresses, all_contacts = self.get_contacts(contacts,
                                                                                                          addresses,
                                                                                                          trading_partnerid)

        # Get payment terms
        payment_terms = header.find('sps:PaymentTerms', ns)
        FOB_related_instruction = header.find('sps:FOBRelatedInstruction', ns)
        customer_payment_terms = ''
        payment_term_id = ''
        if payment_terms is not None:
            customer_payment_terms, payment_term_id = self.get_payment_terms(payment_terms, FOB_related_instruction)

        # Get dates
        dates = header.findall('sps:Dates', ns)
        date_time_qualifier, specific_date = None, None
        for date in dates:
            date_time_qualifier = self.get_ele_text(date, 'DateTimeQualifier')
            specific_date = ''
            if date is not None:
                date_date = self.get_ele_text(date, 'Date')
                date_time = self.get_ele_text(date, 'Time')
                if date_time:
                    specific_date = self.convert_TZ_UTC('%s %s' % (date_date, date_time), is_datetime=True)
                else:
                    specific_date = self.convert_TZ_UTC(date_date)


        carrier_information = header.find('sps:CarrierInformation', ns)
        references = header.find('sps:References', ns)
        notes = header.find('sps:Notes', ns)
        note_code = self.get_ele_text(notes, 'NoteCode')
        note_code = note_code if note_code in ('GEN', 'SHP') else 'GEN'

        # Charges Allowances on Header Level
        charges_allowances = []
        for charge_allow in header.findall('sps:ChargesAllowances', ns):
            charge_record = self.get_charges_allowances(charge_allow)
            charges_allowances.append(charge_record.id)

        edi_user = self.env['res.users'].browse(1)  # Use Odoobot for orders created from EDI

        order_data = {
            'partner_id': partner.id,
            'po_number': po_number,
            'backorder_origin': backorder_origin.id or None,
            'tset_purpose_code': tset_purpose_code if tset_purpose_code in ['00', '06'] else 'NA',
            'primary_PO_type_code': primary_PO_type_code if primary_PO_type_code in ['SA', 'NE', 'PR', 'RO', 'CF'] else 'NA',
            'vendor': vendor,
            'department': department,
            'date_order': date_order,
            'partner_invoice_id': partner_invoice_id.id,
            'partner_shipping_id': partner_shipping_id.id,
            'all_contacts': all_contacts,
            'addresses': addresses,
            'payment_term_id': payment_term_id.id if payment_term_id else None,
            'customer_payment_terms': customer_payment_terms or '',
            'date_time_qualifier': date_time_qualifier or '',
            'commitment_date': specific_date if date_time_qualifier == '002' else None,
            'requested_pickup_date': specific_date if date_time_qualifier == '118' else None,
            'additional_date': specific_date if date_time_qualifier not in ('002', '118') else None,
            'carrier_trans_method_code': self.get_ele_text(carrier_information, 'CarrierTransMethodCode'),
            'carrier_routing': self.get_ele_text(carrier_information, 'CarrierRouting'),
            'reference_qual': self.get_ele_text(references, 'ReferenceQual') if self.get_ele_text(references,'ReferenceQual') in ['12', 'AH', 'IT', 'CT'] else 'NA',
            'reference_id': self.get_ele_text(references, 'ReferenceID'),
            'description': self.get_ele_text(references, 'Description'),
            'note_code': note_code if note_code in ['GEN', 'SHP'] else 'NA',
            'note': self.get_ele_text(notes, 'Note'),
            'charges_allowances': [[6, 0, charges_allowances]],
            'amount_total': self.get_ele_text(summary, 'TotalAmount'),
            'total_line_item_number': self.get_ele_text(summary, 'TotalLineItemNumber'),
            'user_id': edi_user.id,
        }
        return order_data

    def _do_import_so_xml(self, conn, sync_action_id, values):
        '''
        Performs the document synchronization for the new document code
        @param conn : sftp/ftp connection class.
        @param sync_action_id: recordset of type `edi.sync.action`
        @param values:dict of values that may be useful to various methods

        @return bool : return bool (True|False)
        '''

        configs = self.env['edi.config'].search([])
        if not configs or not self.env.company in configs.mapped('company_ids'):
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'title': _("Warning"),
                'sticky': True,
                'message': _('This company is not allowed to perform this action.')
            })
            return False

        conn._connect()
        conn.cd(sync_action_id.dir_path)
        files = conn.ls()
        if not files:
            _logger.warning('Directory on host is empty')

        SaleOrder = self.env['sale.order'].sudo()
        SaleOrderLine = self.env['sale.order.line'].sudo()
        ResPartner = self.env['res.partner'].sudo()
        Product = self.env['product.product']

        for file in files:
            if not file.endswith('.xml'):
                continue

            file_data = conn.download_file(file)

            orders = ET.fromstring(file_data)
            # Skip the file if it is not an 850. It is a 945.
            if 'Orders' not in orders.tag:
                continue
            for order_elem in orders:
                header = order_elem.find('sps:Header', ns)
                orderheader = header.find('sps:OrderHeader', ns)
                trading_partnerid = self.get_ele_text(orderheader, 'TradingPartnerId')

                PO_number = self.get_ele_text(orderheader, 'PurchaseOrderNumber')

                # Check for duplicates. First see if the import claims to be a new order. Then check if duplicate order already exists in db
                if not self._is_new_order(orderheader, PO_number):
                    _logger.warning('Order already created with PO number %s' % PO_number)
                    continue

                trading_partner = ResPartner.search([('trading_partnerid', '=', trading_partnerid),
                                                     ('is_company', '=', True)], limit=1)
                if not trading_partner:
                    _logger.warning('Trading Partner not found for this ID: %s' % trading_partner)
                    continue

                line_item = order_elem.findall('sps:LineItem', ns)
                barcodes = [self.get_ele_text(item.find('sps:OrderLine', ns), "ConsumerPackageCode") for item in line_item]
                part_nums = [self.get_ele_text(item.find('sps:OrderLine', ns), "VendorPartNumber") for item in line_item]
                products = Product.search([('default_code', 'in', part_nums)])
                if not products:
                    products = Product.search([('barcode', 'in', barcodes)])
                if not products:  # For variants, strip the leading and trailing characters
                    products = Product.search([('barcode', 'in', [barcode[1:] for barcode in barcodes])])
                if not products:  # For Case UPC, strip the leading and trailing characters
                    products = Product.search([('barcode', 'in', [barcode[1:-1] for barcode in barcodes])])
                company_id = products.mapped('company_id')[0] if products.mapped('company_id') else None

                order = SaleOrder.create({**self.prepared_order_from_xml(order_elem), **({'company_id': company_id.id} if company_id else {})})
                
                if order:
                    line_item = order_elem.findall('sps:LineItem', ns)
                    line_count = 0
                    for line in line_item:
                        line_data = self.prepared_sale_order_line_from_xml(line, order.id, trading_partner,
                                                                           is_backorder=len(order.backorder_origin))
                        
                        if line_data.get('has_different_ref_barcode', False):
                            order.sudo().message_post(body=_(f'Barcode and Internal Reference are different for: {line_data.get("name")}. from the EDI File of: {file}'))
                        del line_data['has_different_ref_barcode']

                        SaleOrderLine.create(line_data)  # line is one element <OrderLine>
                        line_count = line_count + 1
                    order.write({'total_line_item_number': line_count})
                    order.flush_model()
                    order.sudo().message_post(body=_('Sale Order Created from the EDI File of: %s' % file))

        conn._disconnect()
        return True
