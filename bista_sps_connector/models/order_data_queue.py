# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

import xml.dom.minidom

from xml.dom.minidom import parse

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

from odoo.exceptions import UserError


class OrderDataQueue(models.Model):
    _name = "order.data.queue"
    _description = 'Order Data Queue'
    _inherit = 'mail.thread'

    name = fields.Char(string="Reference", copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submit', 'Submitted'), ('fail', 'Fail')],
        string='Status', help='Connection status of records',
        default='draft', tracking=True)
    edi_config_id = fields.Many2one(
        'edi.config', string='EDI Configuration', tracking=True)
    edi_order = fields.Char("EDI Order", tracking=True)
    edi_type = fields.Selection([('846', 'EDI-846'), ('850', 'EDI-850'), ('855', 'EDI-855'),
                                 ('860', 'EDI-860'), ('865', 'EDI-865'), ('856',
                                                                          'EDI-856'), ('810', 'EDI-810'),
                                 ('811', 'EDI-811')],
                                default='850', readonly=True)
    edi_order_data = fields.Text("Order Data", readonly=True)
    edi_error_log = fields.Text("Error Log", readonly=True)
    # partner_id = fields.Many2one(related="edi_config_id.partner_id", string='Customer')
    sale_order_id = fields.Many2one(
        'sale.order', string="Related Sale Order", readonly=True)
    path = fields.Char(related="edi_config_id.edi_inbound_file_path",
                       string="File Path", tracking=True)
    edi_trading_partner_id = fields.Char(
        string="Trading Partner ID", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        """
            This method creates sequence for each record.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'order.data.queue') or _('New')
        return super(OrderDataQueue, self).create(vals_list)

    def prepare_contact_value(self, contact):
        """
        Define the function to fetch the value from tags and prepare contact
        values.
        @param contact:
        @type contact:
        @return:
        @rtype:
        """
        contact_vals = {}
        contact_type_code_t = contact.getElementsByTagName("ContactTypeCode")
        if contact_type_code_t and contact_type_code_t[0].firstChild:
            contact_vals.update({'edi_contact_type': contact_type_code_t[0].firstChild.data})
        contact_name = contact.getElementsByTagName("ContactName")
        if contact_name and contact_name[0].firstChild:
            contact_vals.update({'name': contact_name[0].firstChild.data})
        contact_email_t = contact.getElementsByTagName("PrimaryEmail")
        if contact_email_t and contact_email_t[0].firstChild:
            contact_vals.update({'email': contact_email_t[0].firstChild.data})
        contact_phone_t = contact.getElementsByTagName("PrimaryPhone")
        if contact_phone_t and contact_phone_t[0].firstChild:
            contact_vals.update({'phone': contact_phone_t[0].firstChild.data})
        contact_fax_t = contact.getElementsByTagName("PrimaryFax")
        if contact_fax_t and contact_fax_t[0].firstChild:
            contact_vals.update({'edi_fax': contact_fax_t[0].firstChild.data})
        contact_vals.update({'type': 'contact'})
        return contact_vals

    def addr_fields(self, addr):
        address_type_code = ''
        loc_code_qualifier = ''
        add_loc_number = ''
        address_name = ''
        address1 = ''
        address2 = ''
        city = ''
        state = self.env['res.country.state']
        zip = ''
        country = self.env['res.country']
        partner_email = ''
        partner_phone = ''
        contact_type_code = ''
        contact_fax = ''
        contact_lst = []
        address_type_code_t = addr.getElementsByTagName("AddressTypeCode")
        if address_type_code_t:
            address_type_code_d = address_type_code_t[0].firstChild
            if address_type_code_d:
                address_type_code = address_type_code_d.data

        loc_code_qualifier_t = addr.getElementsByTagName("LocationCodeQualifier")
        if loc_code_qualifier_t:
            loc_code_qualifier_d = loc_code_qualifier_t[0].firstChild
            if loc_code_qualifier_d:
                loc_code_qualifier = loc_code_qualifier_d.data

        add_loc_number_t = addr.getElementsByTagName("AddressLocationNumber")
        if add_loc_number_t:
            add_loc_number_d = add_loc_number_t[0].firstChild
            if add_loc_number_d:
                add_loc_number = add_loc_number_d.data

        address_name_t = addr.getElementsByTagName("AddressName")
        if address_name_t:
            address_name_d = address_name_t[0].firstChild
            if address_name_d:
                address_name = address_name_d.data
        add_contacts_t = addr.getElementsByTagName("Contacts")
        if add_contacts_t:
            contact_lst.extend(add_contacts_t)
        if add_contacts_t and not partner_email and not partner_phone:
            for add_contact_t in add_contacts_t:
                contact_type_code_t = add_contact_t.getElementsByTagName("ContactTypeCode")
                if contact_type_code_t and contact_type_code_t[0].firstChild:
                    contact_type_code = contact_type_code_t[0].firstChild.data
                contact_email_t = add_contact_t.getElementsByTagName("PrimaryEmail")
                if contact_email_t and contact_email_t[0].firstChild:
                    partner_email = contact_email_t[0].firstChild.data
                contact_phone_t = add_contact_t.getElementsByTagName("PrimaryPhone")
                if contact_phone_t and contact_phone_t[0].firstChild:
                    partner_phone = contact_phone_t[0].firstChild.data
                contact_fax_t = add_contact_t.getElementsByTagName("PrimaryFax")
                if contact_fax_t and contact_fax_t[0].firstChild:
                    contact_fax = contact_fax_t[0].firstChild.data

        address1_t = addr.getElementsByTagName("Address1")
        if address1_t:
            address1_d = address1_t[0].firstChild
            if address1_d:
                address1 = address1_d.data

        address2_t = addr.getElementsByTagName("Address2")
        if address2_t:
            address2_d = address2_t[0].firstChild
            if address2_d:
                address2 = address2_d.data

        city_t = addr.getElementsByTagName("City")
        if city_t:
            city_d = city_t[0].firstChild
            if city_d:
                city = city_d.data

        country_t = addr.getElementsByTagName("Country")
        if country_t:
            country_d = country_t[0].firstChild
            if country_d and country_d.data:
                country = self.env['res.country'].search(
                    [('code', '=', country_d.data)], limit=1)

        state_t = addr.getElementsByTagName("State")
        if state_t and state_t[0].firstChild:
            state_d = state_t[0].firstChild.data
            domain = [('code', '=', state_d)]
            if country:
                domain.append(('country_id', '=', country.id))
            state = self.env['res.country.state'].search(domain, limit=1)

        zip_t = addr.getElementsByTagName("PostalCode")
        if zip_t:
            zip_d = zip_t[0].firstChild
            if zip_d:
                zip = zip_d.data


        address = {
            'name': address_name,
            'edi_st_loc_code_qualifier': loc_code_qualifier,
            'edi_st_addr_loc_number': add_loc_number,
            'address_type_code':address_type_code,
            'edi_st_address_name': address_name,
            'street': address1,
            'street2': address2,
            'city': city,
            'state_id': state.id if state else False,
            'country_id': country.id if country else False,
            'zip': zip,
            'email': partner_email,
            'phone': partner_phone,
            'edi_contact_type': contact_type_code,
            'edi_fax': contact_fax,
        }
        if address_type_code in ['ST', 'DA', 'WH']:
            address.update({'type': 'delivery'})
            # address = {
            #     'type': 'delivery',
            #     'name': address_name,
            #     # 'edi_st_loc_code_qualifier': loc_code_qualifier,
            #     # 'edi_st_addr_loc_number': add_loc_number,
            #     'street': address1,
            #     'street2': address2,
            #     'city': city,
            #     'state_id': state.id if state else False,
            #     'country_id': country.id if country else False,
            #     'zip': zip,
            #  }

        elif address_type_code in ['BT', 'OB']:
            address.update({'type': 'invoice'})
        elif address_type_code in ['BY', 'SO']:
            address.update({'type': 'contact'})
        return address, contact_lst

        # return {'name': address_name,
        #         # 'edi_st_loc_code_qualifier': loc_code_qualifier,
        #         # 'edi_st_addr_loc_number': add_loc_number,
        #         'street': address1,
        #         'street2': address2,
        #         'city': city,
        #         'state_id': state.id if state else False,
        #         'country_id': country.id if country else False,
        #         'zip': zip,
        #         }

        # if address_type_code == 'ST':
        #     return {'edi_st_address_name': address_name,
        #             'edi_st_loc_code_qualifier': loc_code_qualifier,
        #             'edi_st_addr_loc_number': add_loc_number,
        #             'edi_st_address1': address1,
        #             'edi_st_address2': address2,
        #             'edi_st_city': city,
        #             'edi_st_state': state,
        #             'edi_st_country': country,
        #             'edi_st_postal_code': zip,
        #             }
        # elif address_type_code == 'BT':
        #     return {'edi_bt_address_name': address_name,
        #             'edi_bt_loc_code_qualifier': loc_code_qualifier,
        #             'edi_bt_addr_loc_number': add_loc_number,
        #             'edi_bt_address1': address1,
        #             'edi_bt_address2': address2,
        #             'edi_bt_city': city,
        #             'edi_bt_state': state,
        #             'edi_bt_country': country,
        #             'edi_bt_postal_code': zip,
        #             }
        # else:
        #     return False

    def action_import_order_button(self):
        self.with_delay(description="Creating Sale Order for %s" % self.name, max_retries=5).action_import_order()



    def check_trading_partner_field(self, edi_order_data, trading_partner_field_ids):
        """Fetch the value from Partner SPS Field and raise a warning if the required tag value is not in XML."""
        missing_fields = set()
        for record in trading_partner_field_ids.filtered(lambda a:a.document_type=='order_document'):
            field_name = record.trading_partner_field

            if "/" in field_name:
                last_slash_index = field_name.rfind("/")
                parent_tag = field_name[:last_slash_index]
                child_tag = field_name[last_slash_index + 1:]
                parent_elements = edi_order_data.getElementsByTagName(parent_tag)
                if parent_elements:
                    child_elements = parent_elements[0].getElementsByTagName(child_tag)
                    for child_element in child_elements:
                        if child_element.firstChild is None or child_element.firstChild.data.strip() == "":
                            missing_fields.add(field_name)
                            break
                else:
                    missing_fields.add(field_name)
            else:
                field_value = edi_order_data.getElementsByTagName(field_name)
                if not field_value or not field_value[0].childNodes or not field_value[0].childNodes[
                    0].nodeValue.strip():
                    missing_fields.add(field_name)

        missing_fields = list(missing_fields)

        if missing_fields:
            missing_fields_str = ", ".join(missing_fields)
            raise UserError(_("Required tag values '{}' not found in XML.").format(missing_fields_str))

        return True

    def action_import_order(self):
        """
            Button Action to import the order data queue to sales order.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        try:
            xml_data = self.edi_order_data
            name = self.name
            if xml_data:
                self_vals = {}
                address_contacts = []
                edi_error_log = ""
                tset_purpose_code = ""
                customer_ref = ""
                edi_vendor_number = ""
                edi_rec = self.edi_config_id
                partner_env = self.env['res.partner']
                if edi_rec:
                    sale_order_vals = {'edi_config_id': edi_rec.id}
                else:
                    raise ValidationError(_("EDI Config ID Missing for record"))

                DOMTree = xml.dom.minidom.parseString(xml_data)
                edi_order_data = DOMTree.documentElement

                trading_partner_id = edi_order_data.getElementsByTagName("TradingPartnerId")[0].firstChild.data
                if trading_partner_id:
                    partner = partner_env.search(
                        [('trading_partner_id', '=', trading_partner_id)], limit=1)
                    if not partner:
                        raise ValidationError(_("Trading Partner not defined in Odoo System for record"))
                else:
                    raise ValidationError(_("Trading Partner ID missing in XML file. for record"))
                if partner and partner.warehouse_id:
                    sale_order_vals.update({'warehouse_id': partner.warehouse_id.id})
                self.check_trading_partner_field(edi_order_data, partner.trading_partner_field_ids)
                purchase_order_number = edi_order_data.getElementsByTagName("PurchaseOrderNumber")[0].firstChild.data
                tset_purpose_code_t = edi_order_data.getElementsByTagName("TsetPurposeCode")
                if tset_purpose_code_t:
                    tset_purpose_code_d = tset_purpose_code_t[0].firstChild
                    if tset_purpose_code_d:
                        tset_purpose_code = tset_purpose_code_d.data
                primary_po_type_code = edi_order_data.getElementsByTagName("PrimaryPOTypeCode")
                if primary_po_type_code:
                    primary_po_type_code_d = primary_po_type_code[0].firstChild.data
                    if primary_po_type_code_d in ['SA', 'OS', 'RE', 'RC']:
                        sale_order_vals.update({'edi_po_type_code': primary_po_type_code_d})
                currency_t = edi_order_data.getElementsByTagName("BuyersCurrency")
                if currency_t and currency_t[0].firstChild:
                    currency = currency_t[0].firstChild.data
                    sale_order_vals.update({'edi_buyers_currency': currency})
                    currency_id = self.env['res.currency'].search(
                        [('name', '=', currency)], limit=1)
                    if currency_id:
                        sale_order_vals.update({'currency_id': currency_id.id})

                edi_vendor_number_t = edi_order_data.getElementsByTagName("Vendor")
                if edi_vendor_number_t:
                    edi_vendor_number_d = edi_vendor_number_t[0].firstChild
                    if edi_vendor_number_d:
                        edi_vendor_number = edi_vendor_number_d.data

                so_dates = edi_order_data.getElementsByTagName("Dates")
                if so_dates:
                    for date in so_dates:
                        date_type = date.getElementsByTagName("DateTimeQualifier")[0].firstChild.data
                        order_date = date.getElementsByTagName("Date")[0].firstChild.data
                        if date_type == '010':
                            sale_order_vals.update({'date_order': order_date,
                                                    'edi_date_type':date_type
                                                    })
                        if date_type == '002':
                            sale_order_vals.update({'commitment_date': order_date,
                                                    'edi_date_type': date_type
                                                    })

                po_date = edi_order_data.getElementsByTagName("PurchaseOrderDate")[0].firstChild.data
                department_t = edi_order_data.getElementsByTagName("Department")
                if department_t and department_t[0].firstChild:
                    sale_order_vals.update({'edi_department': department_t[0].firstChild.data})
                edi_division_t = edi_order_data.getElementsByTagName("Division")
                if edi_division_t and edi_division_t[0].firstChild:
                    sale_order_vals.update(
                        {'edi_division': edi_division_t[0].firstChild.data})
                customer_ref_t = edi_order_data.getElementsByTagName("CustomerOrderNumber")
                if customer_ref_t:
                    customer_ref = customer_ref_t[0].firstChild.data
                ship_complete_code = edi_order_data.getElementsByTagName("ShipCompleteCode")
                if ship_complete_code and ship_complete_code[0].firstChild:
                    sale_order_vals.update({'edi_ship_comp_code': ship_complete_code[0].firstChild.data})
                # payment_terms = edi_order_data.getElementsByTagName("PaymentTerms")
                # if payment_terms:
                #     terms_description_t = edi_order_data.getElementsByTagName("TermsDescription")
                #     if terms_description_t:
                #         payment_term_name_d = terms_description_t[0].firstChild
                #         if payment_term_name_d:
                #             payment_term_name = payment_term_name_d.data
                #             sale_order_vals.update({'edi_terms_description': payment_term_name})
                payment_terms = edi_order_data.getElementsByTagName("PaymentTerms")
                if payment_terms:
                    edi_payment_terms = {}
                    terms_type = edi_order_data.getElementsByTagName("TermsType")
                    terms_disc_percentage = edi_order_data.getElementsByTagName("TermsDiscountPercentage")
                    terms_disc_duedays = edi_order_data.getElementsByTagName("TermsDiscountDueDays")
                    terms_net_duedays = edi_order_data.getElementsByTagName("TermsNetDueDays")
                    terms_disc_amount = edi_order_data.getElementsByTagName("TermsDiscountAmount")
                    if terms_type and terms_type[0].firstChild:
                        edi_payment_terms.update({'edi_terms_type': terms_type[0].firstChild.data})
                    if terms_disc_percentage and terms_disc_percentage[0].firstChild:
                        edi_payment_terms.update({'edi_terms_disc_percentage': terms_disc_percentage[0].firstChild.data})
                    if terms_disc_duedays and terms_disc_duedays[0].firstChild:
                        edi_payment_terms.update({'edi_terms_disc_duedays': terms_disc_duedays[0].firstChild.data})
                    if terms_net_duedays and terms_net_duedays[0].firstChild:
                        edi_payment_terms.update({'edi_terms_net_duedays': terms_net_duedays[0].firstChild.data})
                    if terms_disc_amount and terms_disc_amount[0].firstChild:
                        edi_payment_terms.update({'edi_terms_disc_amount': terms_disc_amount[0].firstChild.data})
                    if edi_payment_terms:
                        sale_order_vals.update(edi_payment_terms)
                if partner and partner.property_payment_term_id:
                    sale_order_vals.update({'payment_term_id': partner.property_payment_term_id.id})
                if partner and partner.property_product_pricelist:
                    sale_order_vals.update({'pricelist_id': partner.property_product_pricelist.id})
                if partner and partner.edi_outbound_file_path:
                    sale_order_vals.update({'edi_outbound_file_path': partner.edi_outbound_file_path})
                sale_order_vals.update({'partner_id': partner.id,
                                        'partner_invoice_id': partner.id,
                                        'partner_shipping_id': partner.id,
                                        'edi_order_number': purchase_order_number,
                                        'edi_order_date': po_date,
                                        'create_date': po_date,
                                        'client_order_ref': customer_ref,
                                        'edi_trading_partner_id': trading_partner_id,
                                        'edi_tset_purpose_code': tset_purpose_code,
                                        'edi_vendor_number': edi_vendor_number,
                                        'edi_order_data_queue': self.id})
                self_vals.update({'edi_order': purchase_order_number})
                address = edi_order_data.getElementsByTagName("Address")
                if address:
                    contact_ids = shipment_ids = invoice_ids = self.env['res.partner']
                    for addr in address:
                        address_vals, contact_lst = self.addr_fields(addr)
                        if contact_lst:
                            address_contacts.extend(contact_lst)
                        if address_vals:
                            sale_order_vals.update({'edi_st_loc_code_qualifier':address_vals['edi_st_loc_code_qualifier'],
                                                    'edi_st_addr_loc_number':address_vals['edi_st_addr_loc_number'],
                                                    'address_type_code':address_vals['address_type_code'],
                                                    'edi_st_address_name':address_vals['edi_st_address_name'],
                                                    })
                            partner_id = partner_env
                            if address_vals.get('email', False):
                                partner_id = partner_env.search([
                                    ('email', '=', address_vals['email'])], limit=1)
                            if not partner_id and address_vals.get('phone', False):
                                partner_id = partner_env.search([
                                    ('phone', '=', address_vals['phone'])],
                                    limit=1)
                            if not partner_id and address_vals.get('name', False):
                                partner_id = partner_env.search([
                                    ('name', '=', address_vals['name']),
                                    ('type', '=', address_vals.get('type', False))],
                                    limit=1)
                            if not partner_id:
                                partner_id = partner_env.create(address_vals)
                            if partner_id.type == 'contact':
                                contact_ids |= partner_id
                            elif partner_id.type == 'delivery':
                                shipment_ids |= partner_id
    #                             if partner_id.street and partner_id.city and \
    #                                     partner_id.zip and partner_id.state_id:
    #                                 partner_id.geo_localize()
                            elif partner_id.type == 'invoice':
                                invoice_ids |= partner_id
                    invoices = invoice_ids.filtered(lambda l: not l.parent_id)
                    if invoices:
                        if contact_ids.filtered(lambda l: l not in invoices):
                            invoices.update({'parent_id': contact_ids.filtered(lambda l: l not in invoices)[0].id})
                        elif shipment_ids.filtered(lambda l: l not in invoices):
                            invoices.update({'parent_id': shipment_ids.filtered(
                                lambda l: l not in invoices)[0].id})
                        else:
                            parent_invoice = invoices - invoices[0]
                            if parent_invoice:
                                (invoices - parent_invoice).update({'parent_id': parent_invoice.id})

                    shipments = shipment_ids.filtered(lambda l: not l.parent_id)
                    if shipments:
                        if contact_ids.filtered(lambda l: l not in shipments):
                            shipments.update({'parent_id': contact_ids.filtered(lambda l: l not in shipments)[0].id})
                        else:
                            parent_shipment = shipments - shipments[0]
                            if parent_shipment:
                                (shipments - parent_shipment).update(
                                    {'parent_id': parent_shipment.id})
                    contacts = contact_ids.filtered(lambda l: not l.parent_id)
                    if contacts and len(contacts) > 1:
                        parent_contact = contacts - contacts[0]
                        if parent_contact:
                            (contacts - parent_contact).update(
                                {'parent_id': parent_contact.id})
                    # Update the sale order vals.
                    # if contact_ids:
                    #     sale_order_vals.update({'partner_id': contact_ids[0].id})
                    # elif shipment_ids and not contact_ids:
                    #     sale_order_vals.update({'partner_id': shipment_ids[0].id})
                    # elif invoice_ids and not contact_ids and not shipment_ids:
                    #     sale_order_vals.update({'partner_id': invoice_ids[0].id})
                    partner_shiping_id = False
                    if shipment_ids:
                        add_shipment_ids = shipment_ids.filtered(lambda l: l.street and l.zip)
                        if add_shipment_ids:
                            partner_shiping_id = add_shipment_ids[0]
                        else:
                            partner_shiping_id = shipment_ids[0]
                        # sale_order_vals.update({'partner_shipping_id': shipment_ids[0].id})
                    elif not shipment_ids and invoice_ids:
                        partner_shiping_id = invoice_ids[0]
                        # sale_order_vals.update({'partner_shipping_id': invoice_ids[0].id})
                    elif not shipment_ids and not invoice_ids and contact_ids:
                        partner_shiping_id = contact_ids[0]
                    if partner_shiping_id:
                        sale_order_vals.update({'partner_shipping_id': partner_shiping_id.id})

                    # if invoice_ids:
                    #     sale_order_vals.update({'partner_invoice_id': invoice_ids[0].id})
                    # elif shipment_ids and not invoice_ids:
                    #     sale_order_vals.update({'partner_invoice_id': shipment_ids[0].id})
                    # elif not shipment_ids and not invoice_ids and contact_ids:
                    #     sale_order_vals.update({'partner_invoice_id': contact_ids[0].id})

                contacts_t = edi_order_data.getElementsByTagName("Contacts")
                edi_contact_ids = self.env['res.partner']
                for edi_contact in contacts_t:
                    if edi_contact not in address_contacts:
                        contact_vals = self.prepare_contact_value(edi_contact)
                        if contact_vals:
                            contact_id = False
                            if contact_vals.get('email', False):
                                contact_id = partner_env.search([
                                    ('email', '=', contact_vals['email'])], limit=1)
                            if not contact_id and contact_vals.get('phone', False):
                                contact_id = partner_env.search([
                                    ('phone', '=', contact_vals['phone'])],
                                    limit=1)
                            if not contact_id and contact_vals.get('name', False):
                                contact_id = partner_env.search([
                                    ('name', '=', contact_vals['name']),
                                    ('type', '=', 'contact')], limit=1)
                            if not contact_id:
                                contact_id = partner_env.create(contact_vals)
                            edi_contact_ids |= contact_id
                if edi_contact_ids:
                    sale_order_vals.update({
                        'edi_contact_ids': [(6, 0, edi_contact_ids.ids)],
                    })
                carrier_info = edi_order_data.getElementsByTagName("CarrierInformation")
                if carrier_info:
                    carrier_route = carrier_info[0].getElementsByTagName("CarrierRouting")
                    if carrier_route and carrier_route[0].firstChild:
                        sale_order_vals.update({'edi_carrier_route': carrier_route[0].firstChild.data})
                    carrier_alpha_code = carrier_info[0].getElementsByTagName("CarrierAlphaCode")
                    if carrier_alpha_code and carrier_alpha_code[0].firstChild:
                        sale_order_vals.update({'edi_carrier_alpha_code': carrier_alpha_code[0].firstChild.data})
                    carrier_trans_meth_code = carrier_info[0].getElementsByTagName("CarrierTransMethodCode")
                    if carrier_trans_meth_code and carrier_trans_meth_code[0].firstChild:
                        sale_order_vals.update({'edi_carr_trans_meth_code': carrier_trans_meth_code[0].firstChild.data})
                    service_lvl_codes = carrier_info[0].getElementsByTagName("ServiceLevelCodes")
                    if service_lvl_codes :
                        service_lvl_code = service_lvl_codes[0].getElementsByTagName("ServiceLevelCode")
                        if service_lvl_code and service_lvl_code[0].firstChild:
                            sale_order_vals.update({'edi_carr_service_lvl_code': service_lvl_code[0].firstChild.data})

                fob_instruction = edi_order_data.getElementsByTagName("FOBRelatedInstruction")
                if fob_instruction:
                    fob_paycode_t = fob_instruction[0].getElementsByTagName("FOBPayCode")
                    if fob_paycode_t and fob_paycode_t[0].firstChild:
                        sale_order_vals.update({'edi_fob_paycode': fob_paycode_t[0].firstChild.data})
                    fob_description = fob_instruction[0].getElementsByTagName("Description")
                    if fob_description and fob_description[0].firstChild:
                        sale_order_vals.update({'edi_fob_description': fob_description[0].firstChild.data})
                    fob_location_qualifier = fob_instruction[0].getElementsByTagName("FOBLocationDescription")
                    if fob_location_qualifier and fob_location_qualifier[0].firstChild:
                        sale_order_vals.update({'edi_fob_loc_qualifier': fob_location_qualifier[0].firstChild.data})
                    fob_location_description = fob_instruction[0].getElementsByTagName("FOBLocationDescription")
                    if fob_location_description and fob_location_description[0].firstChild:
                        sale_order_vals.update({'edi_fob_loc_description': fob_location_description[0].firstChild.data})

                rest_condition = edi_order_data.getElementsByTagName("RestrictionsOrConditions")
                if rest_condition:
                    rc_qualifier = rest_condition[0].getElementsByTagName("RestrictionsConditionsQualifier")
                    if rc_qualifier and rc_qualifier[0].firstChild:
                        sale_order_vals.update({'edi_rc_qualifier': rc_qualifier[0].firstChild.data})
                    rc_description = rest_condition[0].getElementsByTagName("Description")
                    if rc_description and rc_description[0].firstChild:
                        sale_order_vals.update({'edi_rc_description': rc_description[0].firstChild.data})
                reference_t = edi_order_data.getElementsByTagName("References")
                if reference_t:
                    ref_lst = []
                    for ref in reference_t:
                        ref_dict = {}
                        ref_qual = ref.getElementsByTagName("ReferenceQual")
                        if ref_qual and ref_qual[0].firstChild:
                            ref_dict.update({'edi_ref_qual': ref_qual[0].firstChild.data})
                        ref_id = ref.getElementsByTagName("ReferenceID")
                        if ref_id and ref_id[0].firstChild:
                            ref_dict.update({'edi_ref_id': ref_id[0].firstChild.data})
                        ref_description = ref.getElementsByTagName("Description")
                        if ref_description and ref_description[0].firstChild:
                            ref_dict.update({'edi_ref_description': ref_description[0].firstChild.data})
                        if ref_dict:
                            ref_lst.append((0, 0, ref_dict))
                    if ref_lst:
                        sale_order_vals.update({'edi_reference_ids': ref_lst})
                charge_allowances = edi_order_data.getElementsByTagName("ChargesAllowances")
                if charge_allowances:
                    charge_indicator = charge_allowances[0].getElementsByTagName("AllowChrgIndicator")
                    if charge_indicator and charge_indicator[0].firstChild:
                        sale_order_vals.update({'edi_allow_chrg_indicator': charge_indicator[0].firstChild.data})
                    charge_code = charge_allowances[0].getElementsByTagName("AllowChrgCode")
                    if charge_code and charge_code[0].firstChild:
                        sale_order_vals.update({'edi_allow_chrg_code': charge_code[0].firstChild.data})
                    charge_amt = charge_allowances[0].getElementsByTagName("AllowChrgAmt")
                    if charge_amt and charge_amt[0].firstChild:
                        sale_order_vals.update({'edi_allow_chrg_amt': charge_amt[0].firstChild.data})
                    charge_percent_qual = charge_allowances[0].getElementsByTagName("AllowChrgPercentQual")
                    if charge_percent_qual and charge_percent_qual[0].firstChild:
                        sale_order_vals.update({'edi_allow_chrg_percent_qual': charge_percent_qual[0].firstChild.data})
                    charge_percent = charge_allowances[0].getElementsByTagName("AllowChrgPercent")
                    if charge_percent and charge_percent[0].firstChild:
                        sale_order_vals.update({'edi_allow_chrg_percent': charge_percent[0].firstChild.data})
                    chrg_handling_code = charge_allowances[0].getElementsByTagName("AllowChrgHandlingCode")
                    if chrg_handling_code and chrg_handling_code[0].firstChild:
                        sale_order_vals.update({'edi_allow_ch_handling_code': chrg_handling_code[0].firstChild.data})
                    charge_description = charge_allowances[0].getElementsByTagName("AllowChrgHandlingDescription")
                    if charge_description and charge_description[0].firstChild:
                        sale_order_vals.update({'edi_allow_chrg_description': charge_description[0].firstChild.data})

                notes_t = edi_order_data.getElementsByTagName("Notes")
                if notes_t:
                    note_code = notes_t[0].getElementsByTagName("NoteCode")
                    if note_code and note_code[0].firstChild:
                        sale_order_vals.update({'edi_note_code': note_code[0].firstChild.data})
                    edi_note = notes_t[0].getElementsByTagName("Note")
                    if edi_note and edi_note[0].firstChild:
                        sale_order_vals.update({'note': edi_note[0].firstChild.data})

                line_items = edi_order_data.getElementsByTagName("LineItem")
                order_line_vals = []
                for line_item in line_items:
                    order_line = line_item.getElementsByTagName("OrderLine")
                    product_item_des = edi_order_data.getElementsByTagName("ProductOrItemDescription")
                    order_qty = ""
                    line_seq_number = ""
                    consumer_package_code = ""
                    if order_line:
                        for so_lines in order_line:
                            line_seq_number_t = so_lines.getElementsByTagName("LineSequenceNumber")
                            if line_seq_number_t:
                                line_seq_number_d = line_seq_number_t[0].firstChild
                                if line_seq_number_d:
                                    line_seq_number = line_seq_number_d.data
                            else:
                                continue
                            vendor_part_number_t = so_lines.getElementsByTagName("VendorPartNumber")
                            if vendor_part_number_t and vendor_part_number_t[0].firstChild:
                                vendor_part_number = vendor_part_number_t[0].firstChild.data
                                product_tmpl_id = self.env['product.template'].search(
                                    [('default_code', '=', vendor_part_number)],
                                    limit=1)
                                if not product_tmpl_id:
                                    edi_error_log += "Product does not exists with Internal Reference:- " + str(
                                        vendor_part_number) + "\n"
                                    continue
                                product_id = product_tmpl_id.product_variant_ids[0]
                                if product_tmpl_id and len(product_tmpl_id.product_variant_ids) > 1:
                                    product_id_t = so_lines.getElementsByTagName("ProductID")
                                    if product_id_t:
                                        part_no_t = product_id_t.getElementsByTagName("PartNumber")
                                        if part_no_t and part_no_t[0].firstChild:
                                            product_id_d = product_tmpl_id.product_variant_ids.filtered(
                                                lambda l: l.default_code == part_no_t[0].firstChild.data)
                                            if product_id_d:
                                                product_id = product_id_d[0]
                                buyer_part_number = ''
                                buyer_part_number_t = so_lines.getElementsByTagName("BuyerPartNumber")
                                if buyer_part_number_t and buyer_part_number_t[0].firstChild:
                                    buyer_part_number = so_lines.getElementsByTagName("BuyerPartNumber")[0].firstChild.data
                                consumer_package_code_t = so_lines.getElementsByTagName("ConsumerPackageCode")
                                if consumer_package_code_t and  consumer_package_code_t[0].firstChild:
                                    consumer_package_code = consumer_package_code_t[0].firstChild.data
                                order_qty_t = so_lines.getElementsByTagName("OrderQty")
                                if order_qty_t:
                                    order_qty = order_qty_t[0].firstChild.data
                                    if not order_qty:
                                        edi_error_log += "No Quantity Specified for product " + product_id + "\n"
                                else:
                                    edi_error_log += "Quantity Attribute Missing for Product " + product_id + "\n"
                                line_vals = {
                                    'line_sequence_number': line_seq_number,
                                    's_edi_vendor_prod_code': buyer_part_number,
                                    'product_id': product_id.id,
                                    'product_uom_qty': order_qty,
                                    'edi_order_quantity': order_qty,
                                    'edi_vendor_part_number': consumer_package_code,
                                }
                                purchase_price_t = so_lines.getElementsByTagName("PurchasePrice")
                                if purchase_price_t and purchase_price_t[0].firstChild:
                                    purchase_price = purchase_price_t[0].firstChild.data
                                    line_vals.update({'price_unit': float(purchase_price)})
                                item_description_t = so_lines.getElementsByTagName(
                                    "ProductOrItemDescription")
                                if item_description_t and item_description_t[0].firstChild:
                                    description = item_description_t[0].firstChild.data
                                    line_vals.update({'name': description})
                                upc_casecode = so_lines.getElementsByTagName("UPCCaseCode")
                                if upc_casecode and upc_casecode[0].firstChild:
                                    line_vals.update({'edi_upc_case_code': upc_casecode[0].firstChild.data})
                                order_line_date = line_item.getElementsByTagName("Dates")
                                for l_date in order_line_date:
                                    date_qual = l_date.getElementsByTagName("DateTimeQualifier")[0].firstChild.data
                                    order_date = l_date.getElementsByTagName("Date")[0].firstChild.data
                                    if date_qual == '038':
                                        line_vals.update(
                                            {'edi_latest_ship_date': order_date})
                                    if date_qual == '002':
                                        line_vals.update(
                                            {'edi_delivery_date': order_date})

                                qty_shd_locations = line_item.getElementsByTagName("QuantitiesSchedulesLocations")
                                if qty_shd_locations:
                                    location_qty = qty_shd_locations[0].getElementsByTagName("LocationQuantity")
                                    if location_qty:
                                        location_t = location_qty[0].getElementsByTagName("Location")
                                        if location_t and location_t[0].firstChild:
                                            line_vals.update({'edi_qty_schedule_location': location_t[0].firstChild.data})
                                line_note_t = line_item.getElementsByTagName("Notes")
                                if line_note_t:
                                    line_note_code = line_note_t[0].getElementsByTagName("NoteCode")
                                    if line_note_code and line_note_code[0].firstChild:
                                        line_vals.update({'edi_line_note_code': line_note_code[0].firstChild.data})
                                    edi_line_note = line_note_t[0].getElementsByTagName("Note")
                                    if edi_line_note and edi_line_note[0].firstChild:
                                        line_vals.update({'edi_line_note': edi_line_note[0].firstChild.data})

                                order_qty_uom_t = so_lines.getElementsByTagName("OrderQtyUOM")
                                if order_qty_uom_t:
                                    order_qty_uom = order_qty_uom_t[0].firstChild.data
                                    if order_qty_uom:
                                        uom_id = self.env["uom.uom"].search(
                                            [('edi_uom_code', '=', order_qty_uom)], limit=1)
                                        if uom_id:
                                            line_vals.update({'product_uom': uom_id.id})
                                order_line_vals.append((0, 0, line_vals))
                            else:
                                edi_error_log += "XML file does not have Vendor Part Number. \n"

                        sale_order_vals.update({'order_line': order_line_vals})
                        if edi_error_log:
                            raise ValidationError(_(edi_error_log))
                    if product_item_des:
                        for pro_item in product_item_des:
                            prod_char_code = pro_item.getElementsByTagName("ProductCharacteristicCode")
                            if prod_char_code:
                                prod_char_code_d = prod_char_code[0].firstChild
                                if prod_char_code_d:
                                    edi_prod_char_code = prod_char_code_d.data
                                    sale_order_vals.update({
                                        'edi_prod_char_code':edi_prod_char_code
                                    })
                            prod_description = pro_item.getElementsByTagName("ProductDescription")
                            if prod_description:
                                prod_description_t = prod_description[0].firstChild
                                if prod_description_t:
                                    edi_prod_description_t = prod_description_t.data
                                    sale_order_vals.update({
                                        'edi_prod_description_t': edi_prod_description_t
                                    })

                summary = edi_order_data.getElementsByTagName("Summary")
                if summary:
                    for info in summary:
                        total_line_number_t = info.getElementsByTagName("TotalLineItemNumber")
                        if total_line_number_t:
                            total_line_number_d = total_line_number_t[0].firstChild
                            if total_line_number_d:
                                total_line_number = total_line_number_d.data
                                sale_order_vals.update({'edi_total_line_number': total_line_number})
                        description_t = info.getElementsByTagName("Description")
                        if description_t:
                            description_d = description_t[0].firstChild
                            if description_d:
                                description = description_d.data
                                sale_order_vals.update({'note': description})
                try:
                    sale_order_id = self.env["sale.order"].create(sale_order_vals)
                    # order_list.onchange_partner_id()
                    # calculate the pricelist price on the orderline based on the pricelist configuration.
                    if sale_order_id.pricelist_id:
                        sale_order_id.recompute_pricelist_price()
                    self_vals.update({'sale_order_id': sale_order_id.id})

                except Exception as e:
                    raise ValidationError(_(str(e)))
                else:
                    self_vals.update({'state': 'submit'})
                if self_vals:
                    self.write(self_vals)
        except Exception as e:
            self._cr.rollback()
            self.write({'edi_error_log': str(e),
                        'state': 'fail'})
            self.env.cr.commit()
            raise Warning(_(e))

    def multi_order_data_queue(self):
        """
            This method is used in schedular to import multiple order data queue records to create multiple sale orders.
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        records = self.env['order.data.queue'].search(
            [('state', '=', 'draft')])
        if records:
            for data_queue in records:
                data_queue.with_delay(description="Creating Sale Order for %s" % data_queue.name, max_retries=5).action_import_order()

    def reset_to_draft(self):
        """
            Button action to reset to draft
            :return:
            @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        """
        self.update({'state': 'draft', 'edi_error_log': ''})
