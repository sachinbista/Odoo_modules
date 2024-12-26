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


class OrderDataUpdateQueue(models.Model):
    _name = "order.data.update.queue"
    _description = 'Order Data Update Queue'
    _inherit = 'mail.thread'

    name = fields.Char(string="Reference", copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submit', 'Submitted'), ('fail', 'Fail')],
        string='Status', help='Connection status of records',
        default='draft', tracking=True)
    edi_config_id = fields.Many2one(
        'edi.config', string='EDI Configuration', tracking=True)
    edi_order = fields.Char("EDI Order", tracking=True)
    edi_type = fields.Selection(
        [('846', 'EDI-846'), ('850', 'EDI-850'), ('855', 'EDI-855'),
         ('860', 'EDI-860'), ('865', 'EDI-865'), ('856',
                                                  'EDI-856'),
         ('810', 'EDI-810'),
         ('811', 'EDI-811')],
        default='860', readonly=True)
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
        Override the function to add the sequence of queue.
        @param vals_list:
        @type vals_list:
        @return:
        @rtype:
        """
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'order.data.update.queue') or _('New')
        return super(OrderDataUpdateQueue, self).create(vals_list)

    def prepare_contact_value(self, contact):
        """
        Define the function to fetch the value from tags and prepare contact
        value dict.
        @param contact:
        @type contact:
        @return:
        @rtype:
        """
        contact_vals = {}
        contact_type_code_t = contact.getElementsByTagName("ContactTypeCode")
        if contact_type_code_t and contact_type_code_t[0].firstChild:
            contact_vals.update({'edi_contact_type': contact_type_code_t[0].firstChild.data})
        contact_name =  contact.getElementsByTagName("ContactName")
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

    def prepare_address_values(self, addr):
        """
        Define the function to check the tags value and prepare address value
        dict.
        @param addr:
        @type addr:
        @return:
        @rtype:
        """
        address_type_code = ''
        # loc_code_qualifier = ''
        # add_loc_number = ''
        partner_email = ''
        partner_phone = ''
        address_vals = {}
        contact_lst = []
        address_type_code_t = addr.getElementsByTagName("AddressTypeCode")
        if address_type_code_t:
            address_type_code_d = address_type_code_t[0].firstChild
            if address_type_code_d:
                address_type_code = address_type_code_d.data

        # loc_code_qualifier_t = addr.getElementsByTagName("LocationCodeQualifier")
        # if loc_code_qualifier_t:
        #     loc_code_qualifier_d = loc_code_qualifier_t[0].firstChild
        #     if loc_code_qualifier_d:
        #         loc_code_qualifier = loc_code_qualifier_d.data

        # add_loc_number_t = addr.getElementsByTagName("AddressLocationNumber")
        # if add_loc_number_t:
        #     add_loc_number_d = add_loc_number_t[0].firstChild
        #     if add_loc_number_d:
        #         add_loc_number = add_loc_number_d.data

        address_name_t = addr.getElementsByTagName("AddressName")
        if address_name_t:
            address_name_d = address_name_t[0].firstChild
            if address_name_d:
                address_name = address_name_d.data
                address_vals.update({'name': address_name})

        add_contacts_t = addr.getElementsByTagName("Contacts")
        if add_contacts_t:
            contact_lst.extend(add_contacts_t)
        if add_contacts_t and not partner_email and not partner_phone:
            for add_contact in add_contacts_t:
                contact_type_code_t = add_contact.getElementsByTagName("ContactTypeCode")
                if contact_type_code_t and contact_type_code_t[0].firstChild:
                    address_vals.update({'edi_contact_type': contact_type_code_t[0].firstChild.data})
                contact_email_t = add_contact.getElementsByTagName("PrimaryEmail")
                if contact_email_t and contact_email_t[0].firstChild:
                    partner_email = contact_email_t[0].firstChild.data
                    address_vals.update({'email': partner_email})
                contact_phone_t = add_contact.getElementsByTagName("PrimaryPhone")
                if contact_phone_t and contact_phone_t[0].firstChild:
                    partner_phone = contact_phone_t[0].firstChild.data
                    address_vals.update({'phone': partner_phone})
                contact_fax_t = add_contact.getElementsByTagName("PrimaryFax")
                if contact_fax_t and contact_fax_t[0].firstChild:
                    address_vals.update({'edi_fax': contact_fax_t[0].firstChild.data})

        address1_t = addr.getElementsByTagName("Address1")
        if address1_t:
            address1_d = address1_t[0].firstChild
            if address1_d:
                address1 = address1_d.data
                address_vals.update({'street': address1})
        address2_t = addr.getElementsByTagName("Address2")
        if address2_t:
            address2_d = address2_t[0].firstChild
            if address2_d:
                address2 = address2_d.data
                address_vals.update({'street2': address2})
        city_t = addr.getElementsByTagName("City")
        if city_t:
            city_d = city_t[0].firstChild
            if city_d:
                city = city_d.data
                address_vals.update({'city': city})
        state_t = addr.getElementsByTagName("State")
        if state_t:
            state_d = state_t[0].firstChild
            if state_d and state_d.data:
                state = self.env['res.country.state'].search(
                    [('code', '=', state_d.data)], limit=1)
                address_vals.update({'state_id': state.id if state else False})
        zip_t = addr.getElementsByTagName("PostalCode")
        if zip_t:
            zip_d = zip_t[0].firstChild
            if zip_d:
                zip = zip_d.data
                address_vals.update({'zip': zip})
        country_t = addr.getElementsByTagName("Country")
        if country_t:
            country_d = country_t[0].firstChild
            if country_d and country_d.data:
                country = self.env['res.country'].search(
                    [('code', '=', country_d.data)], limit=1)
                address_vals.update({'country_id': country.id if country else False})
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
        if address_type_code in ['ST', 'DA', 'WH']:
            address_vals.update({'type': 'delivery'})

        elif address_type_code in ['BT', 'OB']:
            address_vals.update({'type': 'invoice'})
        elif address_type_code in ['BY', 'SO']:
            address_vals.update({'type': 'contact'})
        return address_vals, contact_lst

    def action_imp_update_order(self):
        """
        Define the function to fetch the details from tags and update the
        sale order.
        @return:
        @rtype:
        """
        xml_data = self.edi_order_data
        if xml_data:
            self_vals = {}
            address_contacts = []
            sale_update_vals = {}
            partner_env = self.env['res.partner']
            DOMTree = xml.dom.minidom.parseString(xml_data)
            edi_order_data = DOMTree.documentElement
            sale_id = self.env['sale.order']
            purchase_order_number_d = edi_order_data.getElementsByTagName("PurchaseOrderNumber")
            if purchase_order_number_d and purchase_order_number_d[0].firstChild:
                purchase_order_number = purchase_order_number_d[0].firstChild.data
                sale_id = sale_id.search([('edi_order_number', '=', purchase_order_number)], limit=1)
                if not sale_id:
                    self.update({
                        'edi_error_log': "The Order of same PurchaseOrderNumber is not Exist on the Odoo System.\n",
                        'state': 'fail'})
                    return
            else:
                self.update(
                    {'edi_error_log': "PurchaseOrderNumber is missing on the XML File.\n",
                     'state': 'fail'})
                return
            trading_partner_id = edi_order_data.getElementsByTagName("TradingPartnerId")
            if trading_partner_id and trading_partner_id[0].firstChild:
                partner = partner_env.search(
                    [('trading_partner_id', '=', trading_partner_id[0].firstChild.data)], limit=1)
                if not partner:
                    self.update(
                        {'edi_error_log': "Trading Partner not defined in Odoo System.\n", 'state': 'fail'})
                    return
                if partner and sale_id.partner_invoice_id != partner:
                    sale_update_vals.update({'partner_invoice_id': partner.id})
                    if partner.property_product_pricelist:
                        sale_update_vals.update({'pricelist_id': partner.property_product_pricelist.id})
            tset_purpose_code_t = edi_order_data.getElementsByTagName("TsetPurposeCode")
            if tset_purpose_code_t:
                tset_purpose_code_d = tset_purpose_code_t[0].firstChild
                if tset_purpose_code_d:
                    tset_purpose_code = tset_purpose_code_d.data
                    sale_update_vals.update({'edi_tset_purpose_code': tset_purpose_code})
            primary_po_type_code = edi_order_data.getElementsByTagName("PrimaryPOTypeCode")
            if primary_po_type_code and primary_po_type_code[0].firstChild:
                primary_po_type_code_d = primary_po_type_code[0].firstChild.data
                if primary_po_type_code_d in ['SA', 'OS', 'RE', 'RC']:
                    sale_update_vals.update(
                        {'edi_po_type_code': primary_po_type_code_d})
            po_date_t = edi_order_data.getElementsByTagName("PurchaseOrderDate")
            if po_date_t and po_date_t[0].firstChild:
                sale_update_vals.update({'edi_order_date': po_date_t[0].firstChild.data})
            currency_t = edi_order_data.getElementsByTagName("BuyersCurrency")
            if currency_t and currency_t[0].firstChild:
                currency = currency_t[0].firstChild.data
                sale_update_vals.update({'edi_buyers_currency': currency})
                currency_id = self.env['res.currency'].search(
                    [('name', '=', currency)], limit=1)
                if currency_id:
                    sale_update_vals.update({'currency_id': currency_id.id})
            department_t = edi_order_data.getElementsByTagName("Department")
            if department_t and department_t[0].firstChild:
                sale_update_vals.update(
                    {'edi_department': department_t[0].firstChild.data})

            edi_vendor_number_t = edi_order_data.getElementsByTagName("Vendor")
            if edi_vendor_number_t and edi_vendor_number_t[0].firstChild:
                edi_vendor_number = edi_vendor_number_t[0].firstChild.data
                sale_update_vals.update({'edi_vendor_number': edi_vendor_number})

            edi_division_t = edi_order_data.getElementsByTagName("Division")
            if edi_division_t and edi_division_t[0].firstChild:
                sale_update_vals.update(
                    {'edi_division': edi_division_t[0].firstChild.data})
            customer_ref_t = edi_order_data.getElementsByTagName("CustomerOrderNumber")
            if customer_ref_t and customer_ref_t[0].firstChild:
                customer_ref = customer_ref_t[0].firstChild.data
                sale_update_vals.update({'client_order_ref': customer_ref})
            ship_complete_code = edi_order_data.getElementsByTagName("ShipCompleteCode")
            if ship_complete_code and ship_complete_code[0].firstChild:
                sale_update_vals.update({'edi_ship_comp_code': ship_complete_code[0].firstChild.data})
            so_dates = edi_order_data.getElementsByTagName("Dates")
            if so_dates:
                for date in so_dates:
                    date_type = date.getElementsByTagName("DateTimeQualifier")[0].firstChild.data
                    order_date = date.getElementsByTagName("Date")[0].firstChild.data
                    if date_type == '010':
                        sale_update_vals.update({'date_order': order_date})
                    if date_type == '002':
                        sale_update_vals.update({'commitment_date': order_date})
            ###################################################################
            # Added the Address creation Functionality
            address = edi_order_data.getElementsByTagName("Address")
            if address:
                contact_ids = shipment_ids = invoice_ids = self.env['res.partner']
                for addr in address:
                    address_vals, contact_lst = self.prepare_address_values(addr)
                    if contact_lst:
                        address_contacts.extend(contact_lst)
                    if address_vals:
                        partner_id = False
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
                if contact_ids and sale_id.partner_id not in contact_ids:
                    sale_update_vals.update({'partner_id': contact_ids[0].id})
                # elif shipment_ids and not contact_ids and sale_id.partner_id not in shipment_ids:
                #     sale_update_vals.update({'partner_id': shipment_ids[0].id})
                # elif invoice_ids and not contact_ids and not shipment_ids and sale_id.partner_id not in invoice_ids:
                #     sale_update_vals.update({'partner_id': invoice_ids[0].id})
                if shipment_ids and sale_id.partner_shipping_id not in shipment_ids:
                    sale_update_vals.update({'partner_shipping_id': shipment_ids[0].id})
                # elif not shipment_ids and invoice_ids and sale_id.partner_shipping_id not in invoice_ids:
                #     sale_update_vals.update({'partner_shipping_id': invoice_ids[0].id})
                # elif not shipment_ids and not invoice_ids and contact_ids and sale_id.partner_shipping_id not in contact_ids:
                #     sale_update_vals.update({'partner_shipping_id': contact_ids[0].id})

            ##################################################################

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
                edi_contact_ids = edi_contact_ids.filtered(lambda l: l not in sale_id.edi_contact_ids)
                sale_update_vals.update({
                    'edi_contact_ids': [(4, ct_id.id) for ct_id in edi_contact_ids],
                })

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
                    sale_update_vals.update(edi_payment_terms)

            fob_instruction = edi_order_data.getElementsByTagName("FOBRelatedInstruction")
            if fob_instruction:
                fob_paycode_t = fob_instruction[0].getElementsByTagName("FOBPayCode")
                if fob_paycode_t and fob_paycode_t[0].firstChild:
                    sale_update_vals.update({'edi_fob_paycode': fob_paycode_t[0].firstChild.data})
                fob_description = fob_instruction[0].getElementsByTagName("Description")
                if fob_description and fob_instruction[0].firstChild:
                    sale_update_vals.update({'edi_fob_description': fob_description[0].firstChild.data})
                fob_location_qualifier = fob_instruction[0].getElementsByTagName("FOBLocationDescription")
                if fob_location_qualifier and fob_location_qualifier[0].firstChild:
                    sale_update_vals.update({'edi_fob_loc_qualifier': fob_location_qualifier[0].firstChild.data})
                fob_location_description = fob_instruction[0].getElementsByTagName("FOBLocationDescription")
                if fob_location_description and fob_location_description[0].firstChild:
                    sale_update_vals.update({'edi_fob_loc_description': fob_location_description[0].firstChild.data})

            carrier_info = edi_order_data.getElementsByTagName("CarrierInformation")
            if carrier_info:
                carrier_route = carrier_info[0].getElementsByTagName("CarrierRouting")
                if carrier_route and carrier_route[0].firstChild:
                    sale_update_vals.update({'edi_carrier_route': carrier_route[0].firstChild.data})
                carrier_alpha_code = carrier_info[0].getElementsByTagName("CarrierAlphaCode")
                if carrier_alpha_code and carrier_alpha_code[0].firstChild:
                    sale_update_vals.update({'edi_carrier_alpha_code': carrier_alpha_code[0].firstChild.data})
                carrier_trans_meth_code = carrier_info[0].getElementsByTagName("CarrierTransMethodCode")
                if carrier_trans_meth_code and carrier_trans_meth_code[0].firstChild:
                    sale_update_vals.update({'edi_carr_trans_meth_code': carrier_trans_meth_code[0].firstChild.data})

            rest_condition = edi_order_data.getElementsByTagName("RestrictionsOrConditions")
            if rest_condition:
                rc_qualifier = rest_condition[0].getElementsByTagName("RestrictionsConditionsQualifier")
                if rc_qualifier and rc_qualifier[0].firstChild:
                    sale_update_vals.update({'edi_rc_qualifier': rc_qualifier[0].firstChild.data})
                rc_description = rest_condition[0].getElementsByTagName("Description")
                if rc_description and rc_description[0].firstChild:
                    sale_update_vals.update({'edi_rc_description': rc_description[0].firstChild.data})
            reference_t = edi_order_data.getElementsByTagName("References")
            if reference_t:
                ref_lst = []
                ref_rem = False
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
                        if not ref_rem:
                            ref_lst.append((5, 0))
                            ref_rem = True
                        ref_lst.append((0, 0, ref_dict))
                if ref_lst:
                    sale_update_vals.update({'edi_reference_ids': ref_lst})
            charge_allowances = edi_order_data.getElementsByTagName("ChargesAllowances")
            if charge_allowances:
                charge_indicator = charge_allowances[0].getElementsByTagName("AllowChrgIndicator")
                if charge_indicator and charge_indicator[0].firstChild:
                    sale_update_vals.update({'edi_allow_chrg_indicator': charge_indicator[0].firstChild.data})
                charge_code = charge_allowances[0].getElementsByTagName("AllowChrgCode")
                if charge_code and charge_code[0].firstChild:
                    sale_update_vals.update({'edi_allow_chrg_code': charge_code[0].firstChild.data})
                charge_amt = charge_allowances[0].getElementsByTagName("AllowChrgAmt")
                if charge_amt and charge_amt[0].firstChild:
                    sale_update_vals.update({'edi_allow_chrg_amt': charge_amt[0].firstChild.data})
                charge_percent_qual = charge_allowances[0].getElementsByTagName("AllowChrgPercentQual")
                if charge_percent_qual and charge_percent_qual[0].firstChild:
                    sale_update_vals.update({'edi_allow_chrg_percent_qual': charge_percent_qual[0].firstChild.data})
                charge_percent = charge_allowances[0].getElementsByTagName("AllowChrgPercent")
                if charge_percent and charge_percent[0].firstChild:
                    sale_update_vals.update({'edi_allow_chrg_percent': charge_percent[0].firstChild.data})
                chrg_handling_code = charge_allowances[0].getElementsByTagName("AllowChrgHandlingCode")
                if chrg_handling_code and chrg_handling_code[0].firstChild:
                    sale_update_vals.update({'edi_allow_ch_handling_code': chrg_handling_code[0].firstChild.data})
                charge_description = charge_allowances[0].getElementsByTagName("AllowChrgHandlingDescription")
                if charge_description and charge_description[0].firstChild:
                    sale_update_vals.update({'edi_allow_chrg_description': charge_description[0].firstChild.data})

            notes_t = edi_order_data.getElementsByTagName("Notes")
            if notes_t:
                note_code = notes_t[0].getElementsByTagName("NoteCode")
                if note_code and note_code[0].firstChild:
                    sale_update_vals.update({'edi_note_code': note_code[0].firstChild.data})
                edi_note = notes_t[0].getElementsByTagName("Note")
                if edi_note and edi_note[0].firstChild:
                    sale_update_vals.update({'note': edi_note[0].firstChild.data})

            edi_error_log = ''
            line_lst = []
            line_items = edi_order_data.getElementsByTagName("LineItem")
            for line_item in line_items:
                order_line = line_item.getElementsByTagName("OrderLine")
                if order_line:
                    for so_lines in order_line:
                        order_line_vals = {}
                        line_seq_number_t = so_lines.getElementsByTagName("LineSequenceNumber")
                        if line_seq_number_t and line_seq_number_t[0].firstChild:
                            line_seq_number = line_seq_number_t[0].firstChild.data
                            sale_line = sale_id.order_line.filtered(
                                lambda l: l.line_sequence_number == line_seq_number)
                            if sale_line:
                                vendor_part_number_t = so_lines.getElementsByTagName("VendorPartNumber")
                                if vendor_part_number_t and vendor_part_number_t[0].firstChild:
                                    vendor_part_number = vendor_part_number_t[0].firstChild.data
                                    product_tmpl_id = self.env['product.template'].search(
                                        [('default_code', '=', vendor_part_number)],
                                        limit=1)
                                    if not product_tmpl_id:
                                        edi_error_log += "Product does not exists with Internal Refarence:- " + str(
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
                                    order_line_vals.update({'product_id': product_id.id})
                                buyer_part_number_t = so_lines.getElementsByTagName("BuyerPartNumber")
                                if buyer_part_number_t and buyer_part_number_t[0].firstChild:
                                    buyer_part_number = so_lines.getElementsByTagName("BuyerPartNumber")[0].firstChild.data
                                    order_line_vals.update({'s_edi_vendor_prod_code': buyer_part_number,})
                                consumer_package_code_t = so_lines.getElementsByTagName("ConsumerPackageCode")
                                if consumer_package_code_t and  consumer_package_code_t[0].firstChild:
                                    consumer_package_code = consumer_package_code_t[0].firstChild.data
                                    order_line_vals.update({'edi_vendor_part_number': consumer_package_code})
                                order_qty_t = so_lines.getElementsByTagName("OrderQty")
                                if order_qty_t and order_qty_t[0].firstChild:
                                    order_qty = order_qty_t[0].firstChild.data
                                    order_line_vals.update({
                                        'product_uom_qty': order_qty,
                                        'edi_order_quantity': order_qty})
                                purchase_price_t = so_lines.getElementsByTagName("PurchasePrice")
                                if purchase_price_t and purchase_price_t[0].firstChild:
                                    purchase_price = purchase_price_t[0].firstChild.data
                                    order_line_vals.update({'price_unit': float(purchase_price)})
                                item_description_t = so_lines.getElementsByTagName("ProductOrItemDescription")
                                if item_description_t and item_description_t[0].firstChild:
                                    description = item_description_t[0].firstChild.data
                                    order_line_vals.update({'name': description})
                                upc_casecode = so_lines.getElementsByTagName("UPCCaseCode")
                                if upc_casecode and upc_casecode[0].firstChild:
                                    order_line_vals.update({'edi_upc_case_code': upc_casecode[0].firstChild.data})
                                order_line_date = line_item.getElementsByTagName("Dates")
                                for l_date in order_line_date:
                                    date_qual = l_date.getElementsByTagName("DateTimeQualifier")[0].firstChild.data
                                    order_date = l_date.getElementsByTagName("Date")[0].firstChild.data
                                    if date_qual == '038':
                                        order_line_vals.update(
                                            {'edi_latest_ship_date': order_date})
                                    if date_qual == '002':
                                        order_line_vals.update(
                                            {'edi_delivery_date': order_date})

                                qty_shd_locations = line_item.getElementsByTagName("QuantitiesSchedulesLocations")
                                if qty_shd_locations:
                                    location_qty = qty_shd_locations[0].getElementsByTagName("LocationQuantity")
                                    if location_qty:
                                        location_t = location_qty[0].getElementsByTagName("Location")
                                        if location_t and location_t[0].firstChild:
                                            order_line_vals.update({'edi_qty_schedule_location': location_t[0].firstChild.data})
                                line_note_t = line_item.getElementsByTagName("Notes")
                                if line_note_t:
                                    line_note_code = line_note_t[0].getElementsByTagName("NoteCode")
                                    if line_note_code and line_note_code[0].firstChild:
                                        order_line_vals.update({'edi_line_note_code': line_note_code[0].firstChild.data})
                                    edi_line_note = line_note_t[0].getElementsByTagName("Note")
                                    if edi_line_note and edi_line_note[0].firstChild:
                                        order_line_vals.update({'edi_line_note': edi_line_note[0].firstChild.data})

                                order_qty_uom_t = so_lines.getElementsByTagName("OrderQtyUOM")
                                if order_qty_uom_t:
                                    order_qty_uom = order_qty_uom_t[0].firstChild.data
                                    if order_qty_uom:
                                        uom_id = self.env["uom.uom"].search(
                                            [('edi_uom_code', '=', order_qty_uom)], limit=1)
                                        if uom_id:
                                            order_line_vals.update({'product_uom': uom_id.id})
                                if order_line_vals:
                                    line_lst.append((1, sale_line.id, order_line_vals))
                                    # sale_line.write(order_line_vals)
                            else:
                                edi_error_log += 'LineSequenceNumber %s not matching with any order line.' %(str(line_seq_number))
                        else:
                            continue
                        if edi_error_log:
                            self.update(
                                {'edi_error_log': edi_error_log, 'state': 'fail'})
                            return True
                    sale_update_vals.update({'order_line': line_lst})
            summary = edi_order_data.getElementsByTagName("Summary")
            if summary:
                for info in summary:
                    total_line_number_t = info.getElementsByTagName("TotalLineItemNumber")
                    if total_line_number_t:
                        total_line_number_d = total_line_number_t[0].firstChild
                        if total_line_number_d:
                            total_line_number = total_line_number_d.data
                            sale_update_vals.update({'edi_total_line_number': total_line_number})
                    description_t = info.getElementsByTagName("Description")
                    if description_t:
                        description_d = description_t[0].firstChild
                        if description_d:
                            description = description_d.data
                            sale_update_vals.update({'note': description})
            try:
                sale_id.write(sale_update_vals)
                if sale_update_vals.get('pricelist_id', False) and \
                        sale_id.pricelist_id.id == sale_update_vals['pricelist_id']:
                    sale_id.recompute_pricelist_price()
                self_vals.update({
                    'edi_order': purchase_order_number,
                    'sale_order_id': sale_id.id,
                })
            except Exception as e:
                self_vals.update({'edi_error_log': str(e), 'state': 'fail'})
            else:
                self_vals.update({'state': 'submit'})
            if self_vals:
                self.write(self_vals)

    def reset_to_draft(self):
        """
        Define the function to reset to draft stage on queue.
        @return:
        @rtype:
        """
        self.update({'state': 'draft', 'edi_error_log': ''})

    def update_860_order_data(self):
        """
        Define the cron function to process the queue and update the order.
        @return:
        @rtype:
        """
        update_queues = self.env["order.data.update.queue"].search(
             [('state', '=', 'draft')])
        if update_queues:
            for queue in update_queues:
                queue.action_imp_update_order()
