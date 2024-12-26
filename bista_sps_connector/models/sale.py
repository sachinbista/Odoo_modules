# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

import os
import io
import tempfile
import shutil
import logging
import xml.dom.minidom
import base64

from datetime import datetime

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _compute_855_rec_count(self):
        for order in self:
            rec_855_count = self.env['order.ack.data.queue'].search([('so_order_id', '=', order.id)])
            order.rec_855_count = len(rec_855_count.ids)

    edi_config_id = fields.Many2one('edi.config', 'EDI Config', readonly=True)
    edi_outbound_file_path = fields.Char(
        string="Outbound file path", readonly=True)
    edi_order_number = fields.Char(string="EDI Order Number", readonly=True)
    edi_order_date = fields.Datetime(string="EDI Order Date", readonly=True)
    edi_date_type = fields.Char(string="EDI DateTimeQualifier")
    edi_order_ack_dq_id = fields.Many2one(
        'order.ack.data.queue', string="Order Ack Data Queue")
    edi_trading_partner_id = fields.Char(
        string="Trading Partner ID", readonly=True)

    edi_st_address_name = fields.Char(string="Address Name", readonly=True)
    edi_st_address1 = fields.Char(string="Address 1", readonly=True)
    edi_st_address2 = fields.Char(string="Address 2", readonly=True)
    edi_st_city = fields.Char(string="City", readonly=True)
    edi_st_state = fields.Char(string="State", readonly=True)
    edi_st_postal_code = fields.Char(string="Postal Code", readonly=True)
    edi_st_country = fields.Char(string="Country", readonly=True)
    edi_st_addr_loc_number = fields.Char(string="ST-Address Location Number", readonly=True)
    edi_st_loc_code_qualifier = fields.Char(string="ST-Location Code Qualifier", readonly=True)

    edi_bt_address_name = fields.Char(string="Address Name", readonly=True)
    edi_bt_address1 = fields.Char(string="Address1", readonly=True)
    edi_bt_address2 = fields.Char(string="Address2", readonly=True)
    edi_bt_city = fields.Char(string="City", readonly=True)
    edi_bt_state = fields.Char(string="State", readonly=True)
    edi_bt_postal_code = fields.Char(string="Postal Code", readonly=True)
    edi_bt_country = fields.Char(string="Country", readonly=True)
    edi_bt_addr_loc_number = fields.Char(string="BT-Address Location Number", readonly=True)
    edi_bt_loc_code_qualifier = fields.Char(string="BT-Location Code Qualifier", readonly=True)

    edi_order_data_queue = fields.Many2one(
        'order.data.queue', string="Order Data Queue", readonly=True)
    edi_tset_purpose_code = fields.Char(string="EDI TsetPurposeCode", readonly=True)
    edi_vendor_number = fields.Char(string="EDI Vendor", readonly=True)
    edi_total_line_number = fields.Char(string="EDI Total Line Number", readonly=True)
    edi_buyers_currency = fields.Char(string="EDI Buyers Currency", readonly=True)
    rec_855_count = fields.Integer(string='Delivery Orders', compute='_compute_855_rec_count')
    edi_acknowledment_num = fields.Char(string="AcknowledgementNumber")

    def action_view_855_records(self):
        self.ensure_one()
        rec_855_count = self.env['order.ack.data.queue'].search([('so_order_id', '=', self.id)])
        action = self.env["ir.actions.actions"]._for_xml_id("bista_sps_connector.edi_config_855_order_ack_data_queue")

        if len(rec_855_count) > 1:
            action['domain'] = [('id', 'in', rec_855_count.ids)]
        elif rec_855_count:
            form_view = [(self.env.ref('bista_sps_connector.edi_configuration_order_ack_data_queue_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = rec_855_count.id
        return action

    # Custom fields define
    edi_note_code = fields.Char(string="EDI Note Code", readonly=True)
    edi_contact_ids = fields.Many2many('res.partner', string="EDI Contacts", readonly=True)
    edi_ship_comp_code = fields.Char(
        string="EDI ShipCompleteCode", readonly=True)
    edi_po_type_code = fields.Selection([
        ('SA', 'Stand Alone'),
        ('OS', 'Special Order'),
        ('RE', 'Reorder'),
        ('RC', 'Contract')
    ], string="EDI PrimaryPOTypeCode")
    edi_department = fields.Char(string="EDI Department", readonly=True)
    edi_division = fields.Char(string="EDI Division", readonly=True)
    edi_carrier_route = fields.Char(string="EDI CarrierRouting", readonly=True)
    edi_carrier_alpha_code = fields.Char(string="EDI CarrierAlphaCode", readonly=True)
    edi_carr_trans_meth_code = fields.Char(string="EDI CarrierTransMethodCode", readonly=True)
    edi_fob_paycode = fields.Char(string="EDI FOB PayCode", readonly=True)
    edi_fob_description = fields.Char(string="EDI FOB Description", readonly=True)
    edi_fob_loc_qualifier = fields.Char(string="EDI FOB LocationQualifier", readonly=True)
    edi_fob_loc_description = fields.Char(string="EDI FOB LocationDescription", readonly=True)
    edi_rc_qualifier = fields.Char(
        string="EDI RestrictionsConditionsQualifier", readonly=True)
    edi_rc_description = fields.Char(
        string="EDI RestrictionsConditions Description", readonly=True)
    edi_reference_ids = fields.One2many('edi.order.reference', 'sale_id',
                                        string="EDI References")
    edi_allow_chrg_indicator = fields.Char(string="EDI AllowChrgIndicator", readonly=True)
    edi_allow_chrg_code = fields.Char(string="EDI AllowChrgCode", readonly=True)
    edi_allow_chrg_description = fields.Char(string="EDI AllowChrgHandlingDescription", readonly=True)
    edi_allow_chrg_amt = fields.Char(string="EDI AllowChrgAmt", readonly=True)
    edi_allow_chrg_percent_qual = fields.Char(string="EDI AllowChrgPercentQual", readonly=True)
    edi_allow_chrg_percent = fields.Char(string="EDI AllowChrgPercent", readonly=True)
    edi_allow_ch_handling_code = fields.Char(string="EDI AllowChrgHandlingCode", readonly=True)

    edi_terms_type = fields.Char(string="EDi Terms Type", readonly=True)
    edi_terms_disc_percentage = fields.Char(string="EDI TermsDiscountPercentage", readonly=True)
    edi_terms_disc_duedays = fields.Char(string="EDI TermsDiscountDueDays", readonly=True)
    edi_terms_net_duedays = fields.Char(string="EDI TermsNetDueDays", readonly=True)
    edi_terms_disc_amount = fields.Char(string="EDI TermsDiscountAmount", readonly=True)
    # edi_terms_description = fields.Char(string="EDI Terms Description", readonly=True)
    edi_carr_service_lvl_code = fields.Char(string="EDI ServiceLevelCode")
    address_type_code = fields.Char(string="EDI Address Type Code")
    edi_prod_char_code = fields.Char(string="Product Characteristic Code")
    edi_prod_description_t = fields.Char(string="Product Description")

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.edi_order_number:
            invoice_vals.update({
                'edi_order_number': self.edi_order_number,
                'edi_order_date': self.edi_order_date,
                'edi_trading_partner_id': self.edi_trading_partner_id,
                'edi_vendor_number': self.edi_vendor_number,
                'edi_bt_addr_loc_number': self.edi_bt_addr_loc_number,
                'edi_bt_loc_code_qualifier': self.edi_bt_loc_code_qualifier,
                'edi_st_addr_loc_number': self.edi_st_addr_loc_number,
                'edi_st_loc_code_qualifier': self.edi_st_loc_code_qualifier,
                'edi_total_line_number': self.edi_total_line_number,
                'edi_tset_purpose_code': self.edi_tset_purpose_code
            })
        return invoice_vals

    @api.model
    def create(self, vals):
        """
        Ticket 13086 - Cleo EDI Mapping Info
        @author: Akshay Pawar @Bista Solutions Pvt. Ltd.
        :return:
        """
        res = super(SaleOrder, self).create(vals)
        for record in res:
            partner_invoice_id = record.partner_invoice_id
            if partner_invoice_id and partner_invoice_id.edi_config_id and not record.edi_config_id:
                record.update({
                    'edi_config_id': partner_invoice_id.edi_config_id,
                    'edi_trading_partner_id': partner_invoice_id.trading_partner_id,
                    'edi_outbound_file_path': partner_invoice_id.edi_outbound_file_path
                })
        return res

    def write(self, vals):
        """
        Ticket 13086 - Cleo EDI Mapping Info
        @author: Akshay Pawar @Bista Solutions Pvt. Ltd.
        :return:
        """
        res = super(SaleOrder, self).write(vals)
        for record in self:
            partner_invoice_id = record.partner_invoice_id
            if partner_invoice_id and partner_invoice_id.edi_config_id and not record.edi_config_id:
                record.update({
                    'edi_config_id': partner_invoice_id.edi_config_id,
                    'edi_trading_partner_id': partner_invoice_id.trading_partner_id,
                    'edi_outbound_file_path': partner_invoice_id.edi_outbound_file_path
                })
        return res

    def recompute_pricelist_price(self):
        """
        Define the function to get the pricelines and update the pricelist
        price on product lines.
        @return:
        @rtype:
        """
        lines_to_recompute = self._get_update_prices_lines()
        lines_to_recompute.invalidate_recordset(['pricelist_item_id'])
        lines_to_recompute._compute_line_pricelist_price()


    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     """
    #         This method is used to update the payment terms fetched from the EDI file into the Sale Order .
    #         :return:
    #         @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
    #     """
    #     # res = super(SaleOrder, self).onchange_partner_id()
    #     if self.edi_terms_description:
    #         term_id = self.env['account.payment.term'].search([('name', '=', self.edi_terms_description)],
    #                                                           limit=1)
    #         if term_id:
    #             self.update({'payment_term_id': term_id})
        # return res

    def carrier_details(self, record):
        return """
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
                <Date></Date>
                <Time></Time>
                <ReferenceIDs>
                  <ReferenceQual></ReferenceQual>
                  <ReferenceID></ReferenceID>
                </ReferenceIDs>
              </References>
            """

    def prepare_sale_order_xml(self):

        items = """
        <Orders>
           """

        for record in self:
            items += """
            <Order> 
            """
            items += """
                <Meta>
                  <SenderUniqueID></SenderUniqueID>
                  <SenderCompanyName></SenderCompanyName>
                  <ReceiverUniqueID></ReceiverUniqueID>
                  <ReceiverCompanyName></ReceiverCompanyName>
                  <IsDropShip></IsDropShip>
                  <InterchangeControlNumber></InterchangeControlNumber>
                  <GroupControlIdentifier></GroupControlIdentifier>
                  <GroupControlNumber></GroupControlNumber>
                  <DocumentControlIdentifier></DocumentControlIdentifier>
                  <DocumentControlNumber></DocumentControlNumber>
                  <InterchangeSenderID></InterchangeSenderID>
                  <InterchangeReceiverID></InterchangeReceiverID>
                  <GroupSenderID></GroupSenderID>
                  <GroupReceiverID></GroupReceiverID>
                  <BatchPart></BatchPart>
                  <BatchTotal></BatchTotal>
                  <BatchID></BatchID>
                  <Comments></Comments>
                  <Validation></Validation>
                  <OrderManagement></OrderManagement>
                  <Version></Version>
                </Meta>"""

            items += """
                <Header> 
                        """

            items += """
                           <OrderHeader>
                               <TradingPartnerId>%s</TradingPartnerId>
                               <PurchaseOrderNumber>%s</PurchaseOrderNumber>
                               <TsetPurposeCode>%s</TsetPurposeCode>
                               <PrimaryPOTypeCode></PrimaryPOTypeCode>
                               <PrimaryPOTypeDescription></PrimaryPOTypeDescription>
                               <AdditionalPOTypeCodes>
                                 <POTypeCode></POTypeCode>
                                 <POTypeDescription></POTypeDescription>
                               </AdditionalPOTypeCodes>
                               <PurchaseOrderDate>%s</PurchaseOrderDate>
                               <PurchaseOrderTime></PurchaseOrderTime>
                               <ReleaseNumber></ReleaseNumber>
                               <AcknowledgementNumber></AcknowledgementNumber>
                               <AcknowledgementType></AcknowledgementType>
                               <ShipCompleteCode></ShipCompleteCode>
                               <InternalOrderNumber></InternalOrderNumber>
                               <InternalOrderDate></InternalOrderDate>
                               <AcknowledgementDate></AcknowledgementDate>
                               <AcknowledgementTime></AcknowledgementTime>
                               <BuyersCurrency></BuyersCurrency>
                               <SellersCurrency></SellersCurrency>
                               <ExchangeRate></ExchangeRate>
                               <Department></Department>
                               <DepartmentDescription></DepartmentDescription>
                               <Vendor></Vendor>
                               <JobNumber></JobNumber>
                               <Division></Division>
                               <CustomerAccountNumber></CustomerAccountNumber>
                               <CustomerOrderNumber>%s</CustomerOrderNumber>
                               <DocumentVersion></DocumentVersion>
                               <DocumentRevision></DocumentRevision>
                             </OrderHeader> """ % (record.edi_trading_partner_id, record.edi_order_number or '',
                                                   record.edi_tset_purpose_code or '',
                                                   record.edi_order_date.date() or '',
                                                   record.name or '')
            for payment in record.payment_term_id:

                payment_term_name = payment.name
                payment_description = payment.note
                pt_discount_percentage = 0
                # pt_discount_days = 0
                pt_net_days = 0
                pt_discount_amount = ''
                pt_type = ''
                for pt_line in payment.line_ids:
                    pt_type = pt_line.value
                    if pt_type == 'balance':
                        pt_discount_percentage = pt_line.discount_on_amount
                        # pt_discount_days = pt_line.discount_applicable_on_days
                        pt_net_days = pt_line.days

                    elif pt_type == 'percent':
                        pt_discount_percentage = pt_line.value_amount
                        # pt_discount_days = pt_line.discount_applicable_on_days
                        pt_net_days = pt_line.days

                    elif pt_type == 'fixed':
                        pt_discount_amount = pt_line.value_amount
                        # pt_discount_days = pt_line.discount_applicable_on_days
                        pt_net_days = pt_line.days
                    break
                items += """
                            <PaymentTerms>
                                <TermsType>%s</TermsType>
                                <TermsBasisDateCode></TermsBasisDateCode>
                                <TermsTimeRelationCode></TermsTimeRelationCode>
                                <TermsDiscountPercentage>%s</TermsDiscountPercentage>
                                <TermsDiscountDate></TermsDiscountDate>
                                <TermsDiscountDueDays></TermsDiscountDueDays>
                                <TermsNetDueDate></TermsNetDueDate>
                                <TermsNetDueDays>%s</TermsNetDueDays>
                                <TermsDiscountAmount>%s</TermsDiscountAmount>
                                <TermsDeferredDueDate></TermsDeferredDueDate>
                                <TermsDeferredAmountDue></TermsDeferredAmountDue>
                                <PercentOfInvoicePayable></PercentOfInvoicePayable>
                                <TermsDescription>%s</TermsDescription>
                                <TermsDueDay></TermsDueDay>
                                <PaymentMethodCode></PaymentMethodCode>
                                <PaymentMethodID></PaymentMethodID>
                                <LatePaymentChargePercent></LatePaymentChargePercent>
                                <TermsStartDate></TermsStartDate>
                                <TermsDueDateQual></TermsDueDateQual>
                                <AmountSubjectToDiscount></AmountSubjectToDiscount>
                                <DiscountAmountDue></DiscountAmountDue>
                            </PaymentTerms>
                            """ % (pt_type, pt_discount_percentage, pt_net_days, pt_discount_amount,
                                   payment_description or '')

            items += """
                     <Dates>
                        <DateTimeQualifier>055</DateTimeQualifier>
                        <Date>%s</Date>
                        <Time></Time>
                        <DateTimePeriod></DateTimePeriod>
                    </Dates> """ % (record.date_order.date())

            items += """
                    <Contacts>
                    <ContactTypeCode>BD</ContactTypeCode>
                    <ContactName>%s</ContactName>
                    <PrimaryPhone>%s</PrimaryPhone>
                    <PrimaryFax></PrimaryFax>
                    <PrimaryEmail>%s</PrimaryEmail>
                    <AdditionalContactDetails>
                        <ContactQual></ContactQual>
                        <ContactID></ContactID>
                        </AdditionalContactDetails>
                    <ContactReference></ContactReference>
                  </Contacts>
            """ % (record.partner_id.name, record.partner_id.phone or '', record.partner_id.email)

            items += """
                     <Address>
                        <AddressTypeCode>BT</AddressTypeCode>
                        <LocationCodeQualifier></LocationCodeQualifier>
                        <AddressLocationNumber></AddressLocationNumber>
                        <AddressName>%s</AddressName>
                        <AddressAlternateName></AddressAlternateName>
                        <AddressAlternateName2></AddressAlternateName2>
                        <Address1>%s</Address1>
                        <Address2>%s</Address2>
                        <Address3></Address3>
                        <Address4></Address4>
                        <City>%s</City>
                        <State>%s</State>
                        <PostalCode>%s</PostalCode>
                        <Country>%s</Country>
                        <LocationID></LocationID>
                        <CountrySubDivision></CountrySubDivision>
                        <AddressTaxIdNumber></AddressTaxIdNumber>
                        <AddressTaxExemptNumber></AddressTaxExemptNumber>
                        <References>
                          <ReferenceQual></ReferenceQual>
                          <ReferenceID></ReferenceID>
                          <Description></Description>
                          <Date></Date>
                          <Time></Time>
                          <ReferenceIDs>
                            <ReferenceQual></ReferenceQual>
                            <ReferenceID></ReferenceID>
                          </ReferenceIDs>
                        </References>
                        <Contacts>
                          <ContactTypeCode>BD</ContactTypeCode>
                          <ContactName>%s</ContactName>
                          <PrimaryPhone>%s</PrimaryPhone>
                          <PrimaryFax></PrimaryFax>
                          <PrimaryEmail>%s</PrimaryEmail>
                          <AdditionalContactDetails>
                            <ContactQual></ContactQual>
                            <ContactID></ContactID>
                          </AdditionalContactDetails>
                          <ContactReference></ContactReference>
                        </Contacts>
                        <Dates>
                          <DateTimeQualifier></DateTimeQualifier>
                          <Date></Date>
                          <Time></Time>
                          <DateTimePeriod></DateTimePeriod>
                        </Dates>
                    </Address>
            """ % (record.partner_invoice_id.name, record.partner_invoice_id.street or '',
                   record.partner_invoice_id.street2 or '', record.partner_invoice_id.city,
                   record.partner_invoice_id.state_id.code, record.partner_invoice_id.zip,
                   record.partner_invoice_id.country_id.code, record.partner_invoice_id.name,
                   record.partner_invoice_id.phone or '', record.partner_invoice_id.email)
            items += """
               <FOBRelatedInstruction>
                <FOBPayCode></FOBPayCode>
                <FOBLocationQualifier></FOBLocationQualifier>
                <FOBLocationDescription></FOBLocationDescription>
                <FOBTitlePassageCode></FOBTitlePassageCode>
                <FOBTitlePassageLocation></FOBTitlePassageLocation>
                <TransportationTermsType></TransportationTermsType>
                <TransportationTerms></TransportationTerms>
                <RiskOfLossCode></RiskOfLossCode>
                <Description></Description>
              </FOBRelatedInstruction>
                            """

            items += """
                    <CarrierInformation>
                        <StatusCode></StatusCode>
                        <CarrierTransMethodCode></CarrierTransMethodCode>
                        <CarrierAlphaCode></CarrierAlphaCode>
                        <CarrierRouting></CarrierRouting>
                        <EquipmentDescriptionCode></EquipmentDescriptionCode>
                        <CarrierEquipmentInitial></CarrierEquipmentInitial>
                        <CarrierEquipmentNumber></CarrierEquipmentNumber>
                        <EquipmentType></EquipmentType>
                        <OwnershipCode></OwnershipCode>
                        <RoutingSequenceCode></RoutingSequenceCode>
                        <TransitDirectionCode></TransitDirectionCode>
                        <TransitTimeQual></TransitTimeQual>
                        <TransitTime></TransitTime>
                    <ServiceLevelCodes>
                      <ServiceLevelCode></ServiceLevelCode>
                    </ServiceLevelCodes>
                    <Address>
                      <AddressTypeCode>ST</AddressTypeCode>
                      <LocationCodeQualifier></LocationCodeQualifier>
                      <AddressLocationNumber></AddressLocationNumber>
                      <AddressName>%s</AddressName>
                      <AddressAlternateName></AddressAlternateName>
                      <AddressAlternateName2></AddressAlternateName2>
                      <Address1>%s</Address1>
                      <Address2>%s</Address2>
                      <Address3></Address3>
                      <Address4></Address4>
                      <City>%s</City>
                      <State>%s</State>
                      <PostalCode>%s</PostalCode>
                      <Country>%s</Country>
                      <LocationID></LocationID>
                      <CountrySubDivision></CountrySubDivision>
                      <AddressTaxIdNumber></AddressTaxIdNumber>
                      <AddressTaxExemptNumber></AddressTaxExemptNumber>
                      <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                        <Time></Time>
                        <DateTimePeriod></DateTimePeriod>
                      </Dates>
                    </Address>
                    <SealNumbers>
                      <SealStatusCode></SealStatusCode>
                      <SealNumber></SealNumber>
                    </SealNumbers>
                  </CarrierInformation>
                       """ % (record.partner_shipping_id.name,
                              record.partner_shipping_id.street, record.partner_shipping_id.street2,
                              record.partner_shipping_id.city,
                              record.partner_shipping_id.state_id.code, record.partner_shipping_id.zip,
                              record.partner_shipping_id.country_id.code)

            items += self.carrier_details(record)
            # items += """
            # <References>
            #     <ReferenceQual>2I</ReferenceQual>
            #     <ReferenceID>%s</ReferenceID>
            #     <Description>%s</Description>
            #     <Date></Date>
            #     <Time></Time>
            #     <ReferenceIDs>
            #       <ReferenceQual></ReferenceQual>
            #       <ReferenceID></ReferenceID>
            #     </ReferenceIDs>
            #   </References>
            # """ % (record.tracking_no or '', record.preferred_carrier_id or '')
            items += """
              <Notes>
                <NoteCode>GEN</NoteCode>
                <Note>%s</Note>
                <LanguageCode></LanguageCode>
              </Notes>
              <Commodity>
                <CommodityCodeQualifier></CommodityCodeQualifier>
                <CommodityCode></CommodityCode>
              </Commodity>
            """ % record.note

            items += """
             <Taxes>
                <TaxTypeCode></TaxTypeCode>
                <TaxAmount></TaxAmount>
                <TaxPercentQual></TaxPercentQual>
                <TaxPercent></TaxPercent>
                <JurisdictionQual></JurisdictionQual>
                <JurisdictionCode></JurisdictionCode>
                <TaxExemptCode></TaxExemptCode>
                <RelationshipCode></RelationshipCode>
                <PercentDollarBasis></PercentDollarBasis>
                <TaxHandlingCode></TaxHandlingCode>
                <TaxID></TaxID>
                <AssignedID></AssignedID>
                <Description></Description>
              </Taxes>
            
            """

            items += """
             <ChargesAllowances>
                <AllowChrgIndicator></AllowChrgIndicator>
                <AllowChrgCode></AllowChrgCode>
                <AllowChrgAgencyCode></AllowChrgAgencyCode>
                <AllowChrgAgency></AllowChrgAgency>
                <AllowChrgAmt></AllowChrgAmt>
                <AllowChrgPercentQual></AllowChrgPercentQual>
                <AllowChrgPercent></AllowChrgPercent>
                <PercentDollarBasis></PercentDollarBasis>
                <AllowChrgRate></AllowChrgRate>
                <AllowChrgQtyUOM></AllowChrgQtyUOM>
                <AllowChrgQty></AllowChrgQty>
                <AllowChrgHandlingCode></AllowChrgHandlingCode>
                <ReferenceIdentification></ReferenceIdentification>
                <AllowChrgHandlingDescription></AllowChrgHandlingDescription>
                <OptionNumber></OptionNumber>
                <ExceptionNumber></ExceptionNumber>
                <AllowChrgQty2></AllowChrgQty2>
                <LanguageCode></LanguageCode>
                <CalculationSequence></CalculationSequence>
                <Taxes>
                  <TaxTypeCode></TaxTypeCode>
                  <TaxAmount></TaxAmount>
                  <TaxPercentQual></TaxPercentQual>
                  <TaxPercent></TaxPercent>
                  <JurisdictionQual></JurisdictionQual>
                  <JurisdictionCode></JurisdictionCode>
                  <TaxExemptCode></TaxExemptCode>
                  <RelationshipCode></RelationshipCode>
                  <PercentDollarBasis></PercentDollarBasis>
                  <TaxHandlingCode></TaxHandlingCode>
                  <TaxID></TaxID>
                  <AssignedID></AssignedID>
                  <Description></Description>
                </Taxes>
              </ChargesAllowances>
            """

            items += """
                <QuantityAndWeight>
                    <PackingMedium></PackingMedium>
                    <PackingMaterial></PackingMaterial>
                    <LadingQuantity></LadingQuantity>
                    <LadingDescription></LadingDescription>
                    <WeightQualifier></WeightQualifier>
                    <Weight></Weight>
                    <WeightUOM></WeightUOM>
                    <Volume></Volume>
                    <VolumeUOM></VolumeUOM>
                    <PalletExchangeCode></PalletExchangeCode>
                </QuantityAndWeight>
            """

            items += """
             <QuantityTotals>
                <QuantityTotalsQualifier></QuantityTotalsQualifier>
                <Quantity></Quantity>
                <QuantityUOM></QuantityUOM>
                <WeightQualifier></WeightQualifier>
                <Weight></Weight>
                <WeightUOM></WeightUOM>
                <Volume></Volume>
                <VolumeUOM></VolumeUOM>
                <Description></Description>
              </QuantityTotals>
            """

            items += """
              <RegulatoryCompliances>
                <RegulatoryComplianceQual></RegulatoryComplianceQual>
                <YesOrNoResponse></YesOrNoResponse>
                <RegulatoryComplianceID></RegulatoryComplianceID>
                <RegulatoryAgency></RegulatoryAgency>
                <Description></Description>
              </RegulatoryCompliances>
            """

            items += """</Header>
            """
            # count = 0
            for line in record.order_line:
                # count += 1
                items += """
                <LineItem>
                            """
                items += """
                   <OrderLine>
                       <LineSequenceNumber>%s</LineSequenceNumber>
                       <ApplicationId></ApplicationId>
                       <BuyerPartNumber>%s</BuyerPartNumber>
                       <VendorPartNumber></VendorPartNumber>
                       <ConsumerPackageCode>%s</ConsumerPackageCode>
                       <EAN></EAN>
                       <GTIN></GTIN>
                       <UPCCaseCode></UPCCaseCode>
                       <NatlDrugCode></NatlDrugCode>
                       <InternationalStandardBookNumber></InternationalStandardBookNumber>
                       <ProductID>
                         <PartNumberQual></PartNumberQual>
                         <PartNumber></PartNumber>
                       </ProductID>
                       <OrderQty>%s</OrderQty>
                       <OrderQtyUOM>%s</OrderQtyUOM>
                       <PurchasePriceType></PurchasePriceType>
                       <PurchasePrice>%s</PurchasePrice>
                       <PurchasePriceBasis></PurchasePriceBasis>
                       <BuyersCurrency></BuyersCurrency>
                       <SellersCurrency></SellersCurrency>
                       <ExchangeRate></ExchangeRate>
                       <ShipDate></ShipDate>
                       <ExtendedItemTotal></ExtendedItemTotal>
                       <ProductSizeCode></ProductSizeCode>
                       <ProductSizeDescription></ProductSizeDescription>
                       <ProductColorCode></ProductColorCode>
                       <ProductColorDescription></ProductColorDescription>
                       <ProductMaterialCode></ProductMaterialCode>
                       <ProductMaterialDescription>%s</ProductMaterialDescription>
                       <ProductProcessCode></ProductProcessCode>
                       <ProductProcessDescription></ProductProcessDescription>
                       <Department></Department>
                       <DepartmentDescription></DepartmentDescription>
                       <Class></Class>
                       <Gender></Gender>
                       <SellerDateCode></SellerDateCode>
                       <NRFStandardColorAndSize>
                         <NRFColorCode></NRFColorCode>
                         <ColorCategoryName></ColorCategoryName>
                         <ColorPrimaryDescription></ColorPrimaryDescription>
                         <NRFSizeCode></NRFSizeCode>
                         <SizeCategoryName></SizeCategoryName>
                         <SizePrimaryDescription></SizePrimaryDescription>
                         <SizeSecondaryDescription></SizeSecondaryDescription>
                         <SizeTableName></SizeTableName>
                         <SizeHeading1></SizeHeading1>
                         <SizeHeading2></SizeHeading2>
                         <SizeHeading3></SizeHeading3>
                         <SizeHeading4></SizeHeading4>
                       </NRFStandardColorAndSize>
                   </OrderLine>
                """ % (line.line_sequence_number, line.s_edi_vendor_prod_code or '', line.product_id.barcode or '',
                       line.edi_order_quantity, line.product_uom.name, line.price_unit, line.product_id.name)
                items += """
                    <LineItemAcknowledgement>
                """
                if record.state == 'cancel' or line.product_uom_qty == 0.00:
                    items += """
                        <ItemStatusCode>R</ItemStatusCode>
                    """
                elif record.state in ('done', 'sale') and line.product_uom_qty == line.edi_order_quantity:
                    items += """
                        <ItemStatusCode>A</ItemStatusCode>
                    """
                else:
                    items += """
                        <ItemStatusCode>C</ItemStatusCode>
                    """
                items += """
                        <LineSequenceNumber>%s</LineSequenceNumber>
                        <ItemScheduleQty>%s</ItemScheduleQty>
                        <ItemScheduleUOM>%s</ItemScheduleUOM>
                    <ItemScheduleQualifier></ItemScheduleQualifier>
                    <ItemScheduleDate></ItemScheduleDate>
                    <BuyerPartNumber>%s</BuyerPartNumber>
                    <VendorPartNumber></VendorPartNumber>
                    <ConsumerPackageCode>%s</ConsumerPackageCode>
                    <EAN></EAN>
                    <GTIN></GTIN>
                    <UPCCaseCode></UPCCaseCode>
                    <NatlDrugCode></NatlDrugCode>
                    <InternationalStandardBookNumber></InternationalStandardBookNumber>
                    <ProductID>
                      <PartNumberQual></PartNumberQual>
                      <PartNumber></PartNumber>
                    </ProductID>
                    <PurchasePriceType></PurchasePriceType>
                    <PurchasePrice>%s</PurchasePrice>
                    <PurchasePriceBasis></PurchasePriceBasis>
                    <BuyersCurrency></BuyersCurrency>
                    <SellersCurrency></SellersCurrency>
                    <ExchangeRate></ExchangeRate>
                    <ExtendedItemTotal></ExtendedItemTotal>
                    <ProductSizeCode></ProductSizeCode>
                    <ProductSizeDescription></ProductSizeDescription>
                    <ProductColorCode></ProductColorCode>
                    <ProductColorDescription></ProductColorDescription>
                    <ProductMaterialCode></ProductMaterialCode>
                    <ProductMaterialDescription>%s</ProductMaterialDescription>
                    <ProductProcessCode></ProductProcessCode>
                    <ProductProcessDescription></ProductProcessDescription>
                    <Department></Department>
                    <DepartmentDescription></DepartmentDescription>
                    <Class></Class>
                    <Gender></Gender>
                    <IndustryCode></IndustryCode>
                </LineItemAcknowledgement>
                """ % (line.line_sequence_number, line.product_uom_qty, line.product_uom.display_name,
                       line.s_edi_vendor_prod_code or '',
                       line.product_id.barcode or '', line.price_unit, line.product_id.name)

                items += """
                    <Dates>
                    <DateTimeQualifier></DateTimeQualifier>
                    <Date></Date>
                    <Time></Time>
                    <DateTimePeriod></DateTimePeriod>
                  </Dates>
                """

                items += """
                
                    <Measurements>
                        <MeasurementRefIDCode></MeasurementRefIDCode>
                        <MeasurementQualifier></MeasurementQualifier>
                        <MeasurementValue></MeasurementValue>
                        <CompositeUOM></CompositeUOM>
                        <RangeMinimum></RangeMinimum>
                        <RangeMaximum></RangeMaximum>
                        <MeasurementSignificanceCode></MeasurementSignificanceCode>
                        <MeasurementAttributeCode></MeasurementAttributeCode>
                        <SurfaceLayerPositionCode></SurfaceLayerPositionCode>
                        <IndustryCodeQualifier></IndustryCodeQualifier>
                        <IndustryCode></IndustryCode>
                    </Measurements>
                """

                items += """
                <PriceInformation>
                    <ChangeReasonCode></ChangeReasonCode>
                    <EffectiveDate></EffectiveDate>
                    <PriceTypeIDCode></PriceTypeIDCode>
                    <UnitPrice></UnitPrice>
                    <UnitPriceBasis></UnitPriceBasis>
                    <UnitPriceBasisMultiplier></UnitPriceBasisMultiplier>
                    <Currency></Currency>
                    <PriceMultiplierQual></PriceMultiplierQual>
                    <PriceMultiplier></PriceMultiplier>
                    <RebateAmount></RebateAmount>
                    <Quantity></Quantity>
                    <QuantityUOM></QuantityUOM>
                    <MultiplePriceQuantity></MultiplePriceQuantity>
                    <ClassOfTradeCode></ClassOfTradeCode>
                    <ConditionValue></ConditionValue>
                    <Description></Description>
                </PriceInformation>
                """

                items += """
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode></ProductCharacteristicCode>
                        <AgencyQualifierCode></AgencyQualifierCode>
                        <ProductDescriptionCode></ProductDescriptionCode>
                        <ProductDescription></ProductDescription>
                        <SurfaceLayerPositionCode></SurfaceLayerPositionCode>
                        <SourceSubqualifier></SourceSubqualifier>
                        <YesOrNoResponse></YesOrNoResponse>
                        <LanguageCode></LanguageCode>
                    </ProductOrItemDescription>
                """

                items += """
                <MasterItemAttribute>
                    <ItemAttribute>
                      <ItemAttributeQualifier></ItemAttributeQualifier>
                      <Value></Value>
                      <ValueUOM></ValueUOM>
                      <Description></Description>
                      <YesOrNoResponse></YesOrNoResponse>
                      <Measurements>
                        <MeasurementRefIDCode></MeasurementRefIDCode>
                        <MeasurementQualifier></MeasurementQualifier>
                        <MeasurementValue></MeasurementValue>
                        <CompositeUOM></CompositeUOM>
                        <RangeMinimum></RangeMinimum>
                        <RangeMaximum></RangeMaximum>
                        <MeasurementSignificanceCode></MeasurementSignificanceCode>
                        <MeasurementAttributeCode></MeasurementAttributeCode>
                        <SurfaceLayerPositionCode></SurfaceLayerPositionCode>
                        <IndustryCodeQualifier></IndustryCodeQualifier>
                        <IndustryCode></IndustryCode>
                      </Measurements>
                    </ItemAttribute>
                </MasterItemAttribute>
                """

                items += """
                    <PhysicalDetails>
                        <PackQualifier></PackQualifier>
                        <PackValue></PackValue>
                        <PackSize></PackSize>
                        <PackUOM></PackUOM>
                        <PackingMedium></PackingMedium>
                        <PackingMaterial></PackingMaterial>
                        <WeightQualifier></WeightQualifier>
                        <PackWeight></PackWeight>
                        <PackWeightUOM></PackWeightUOM>
                        <PackVolume></PackVolume>
                        <PackVolumeUOM></PackVolumeUOM>
                        <PackLength></PackLength>
                        <PackWidth></PackWidth>
                        <PackHeight></PackHeight>
                        <DimensionUOM></DimensionUOM>
                        <Description></Description>
                        <SurfaceLayerPositionCode></SurfaceLayerPositionCode>
                        <AssignedID></AssignedID>
                    </PhysicalDetails>
                 """

                items += """
                <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
                <Date></Date>
                <Time></Time>
                <ReferenceIDs>
                  <ReferenceQual></ReferenceQual>
                  <ReferenceID></ReferenceID>
                </ReferenceIDs>
              </References>
                """
                items += """
                <Notes>
                    <NoteCode></NoteCode>
                    <Note></Note>
                    <LanguageCode></LanguageCode>
                </Notes>
                  <Commodity>
                    <CommodityCodeQualifier></CommodityCodeQualifier>
                    <CommodityCode></CommodityCode>
                  </Commodity>
                """

                items += """
                <Address>
                    <AddressTypeCode></AddressTypeCode>
                    <LocationCodeQualifier></LocationCodeQualifier>
                    <AddressLocationNumber></AddressLocationNumber>
                    <AddressName></AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <AddressAlternateName2></AddressAlternateName2>
                    <Address1></Address1>
                    <Address2></Address2>
                    <Address3></Address3>
                    <Address4></Address4>
                    <City></City>
                    <State></State>
                    <PostalCode></PostalCode>
                    <Country></Country>
                    <LocationID></LocationID>
                    <CountrySubDivision></CountrySubDivision>
                    <AddressTaxIdNumber></AddressTaxIdNumber>
                    <AddressTaxExemptNumber></AddressTaxExemptNumber>
                    <References>
                      <ReferenceQual></ReferenceQual>
                      <ReferenceID></ReferenceID>
                      <Description></Description>
                      <Date></Date>
                      <Time></Time>
                      <ReferenceIDs>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                      </ReferenceIDs>
                    </References>
                    <Contacts>
                      <ContactTypeCode></ContactTypeCode>
                      <ContactName></ContactName>
                      <PrimaryPhone></PrimaryPhone>
                      <PrimaryFax></PrimaryFax>
                      <PrimaryEmail></PrimaryEmail>
                      <AdditionalContactDetails>
                        <ContactQual></ContactQual>
                        <ContactID></ContactID>
                      </AdditionalContactDetails>
                      <ContactReference></ContactReference>
                    </Contacts>
                    <Dates>
                      <DateTimeQualifier></DateTimeQualifier>
                      <Date></Date>
                      <Time></Time>
                      <DateTimePeriod></DateTimePeriod>
                    </Dates>
                </Address>
                """

                items += """<Subline>
                """

                items += """
                    <SublineItemDetail>
                      <LineSequenceNumber></LineSequenceNumber>
                      <ApplicationId></ApplicationId>
                      <BuyerPartNumber></BuyerPartNumber>
                      <VendorPartNumber></VendorPartNumber>
                      <ConsumerPackageCode></ConsumerPackageCode>
                      <EAN></EAN>
                      <GTIN></GTIN>
                      <UPCCaseCode></UPCCaseCode>
                      <NatlDrugCode></NatlDrugCode>
                      <InternationalStandardBookNumber></InternationalStandardBookNumber>
                      <ProductID>
                        <PartNumberQual></PartNumberQual>
                        <PartNumber></PartNumber>
                      </ProductID>
                      <ProductSizeCode></ProductSizeCode>
                      <ProductSizeDescription></ProductSizeDescription>
                      <ProductColorCode></ProductColorCode>
                      <ProductColorDescription></ProductColorDescription>
                      <ProductMaterialCode></ProductMaterialCode>
                      <ProductMaterialDescription></ProductMaterialDescription>
                      <ProductProcessCode></ProductProcessCode>
                      <ProductProcessDescription></ProductProcessDescription>
                      <QtyPer></QtyPer>
                      <QtyPerUOM></QtyPerUOM>
                      <PurchasePriceType></PurchasePriceType>
                      <PurchasePrice></PurchasePrice>
                      <PurchasePriceBasis></PurchasePriceBasis>
                      <Gender></Gender>
                      <NRFStandardColorAndSize>
                        <NRFColorCode></NRFColorCode>
                        <ColorCategoryName></ColorCategoryName>
                        <ColorPrimaryDescription></ColorPrimaryDescription>
                        <NRFSizeCode></NRFSizeCode>
                        <SizeCategoryName></SizeCategoryName>
                        <SizePrimaryDescription></SizePrimaryDescription>
                        <SizeSecondaryDescription></SizeSecondaryDescription>
                        <SizeTableName></SizeTableName>
                        <SizeHeading1></SizeHeading1>
                        <SizeHeading2></SizeHeading2>
                        <SizeHeading3></SizeHeading3>
                        <SizeHeading4></SizeHeading4>
                      </NRFStandardColorAndSize>
                </SublineItemDetail>
                
                """

                items += """
                       <Dates>
                       <DateTimeQualifier></DateTimeQualifier>
                       <Date></Date>
                       <Time></Time>
                       <DateTimePeriod></DateTimePeriod>
                     </Dates>
                               """

                items += """
                    <PriceInformation>
                      <ChangeReasonCode></ChangeReasonCode>
                      <EffectiveDate></EffectiveDate>
                      <PriceTypeIDCode></PriceTypeIDCode>
                      <UnitPrice></UnitPrice>
                      <UnitPriceBasis></UnitPriceBasis>
                      <UnitPriceBasisMultiplier></UnitPriceBasisMultiplier>
                      <Currency></Currency>
                      <PriceMultiplierQual></PriceMultiplierQual>
                      <PriceMultiplier></PriceMultiplier>
                      <RebateAmount></RebateAmount>
                      <Quantity></Quantity>
                      <QuantityUOM></QuantityUOM>
                      <MultiplePriceQuantity></MultiplePriceQuantity>
                      <ClassOfTradeCode></ClassOfTradeCode>
                      <ConditionValue></ConditionValue>
                      <Description></Description>
                    </PriceInformation>
                """

                items += """
                    <ProductOrItemDescription>
                      <ProductCharacteristicCode></ProductCharacteristicCode>
                      <AgencyQualifierCode></AgencyQualifierCode>
                      <ProductDescriptionCode></ProductDescriptionCode>
                      <ProductDescription></ProductDescription>
                      <SurfaceLayerPositionCode></SurfaceLayerPositionCode>
                      <SourceSubqualifier></SourceSubqualifier>
                      <YesOrNoResponse></YesOrNoResponse>
                      <LanguageCode></LanguageCode>
                    </ProductOrItemDescription>
                """

                items += """
                    <PhysicalDetails>
                      <PackQualifier></PackQualifier>
                      <PackValue></PackValue>
                      <PackSize></PackSize>
                      <PackUOM></PackUOM>
                      <PackingMedium></PackingMedium>
                      <PackingMaterial></PackingMaterial>
                      <WeightQualifier></WeightQualifier>
                      <PackWeight></PackWeight>
                      <PackWeightUOM></PackWeightUOM>
                      <PackVolume></PackVolume>
                      <PackVolumeUOM></PackVolumeUOM>
                      <PackLength></PackLength>
                      <PackWidth></PackWidth>
                      <PackHeight></PackHeight>
                      <DimensionUOM></DimensionUOM>
                      <Description></Description>
                      <SurfaceLayerPositionCode></SurfaceLayerPositionCode>
                      <AssignedID></AssignedID>
                    </PhysicalDetails>
                """

                items += """
                    <References>
                      <ReferenceQual></ReferenceQual>
                      <ReferenceID></ReferenceID>
                      <Description></Description>
                      <Date></Date>
                      <Time></Time>
                      <ReferenceIDs>
                    <ReferenceQual></ReferenceQual>
                    <ReferenceID></ReferenceID>
                    </ReferenceIDs>
                    </References>
                    <Notes>
                      <NoteCode></NoteCode>
                      <Note></Note>
                      <LanguageCode></LanguageCode>
                    </Notes>
                """

                for tax in line.tax_id:
                    items += """
                    
                      <Taxes>
                      <TaxTypeCode>%s</TaxTypeCode>
                      <TaxAmount></TaxAmount>
                      <TaxPercentQual></TaxPercentQual>
                      <TaxPercent>%s</TaxPercent>
                      <JurisdictionQual></JurisdictionQual>
                      <JurisdictionCode></JurisdictionCode>
                      <TaxExemptCode></TaxExemptCode>
                      <RelationshipCode></RelationshipCode>
                      <PercentDollarBasis></PercentDollarBasis>
                      <TaxHandlingCode></TaxHandlingCode>
                      <TaxID></TaxID>
                      <AssignedID></AssignedID>
                      <Description>%s</Description>
                    </Taxes>
                    """ % (tax.type_tax_use, tax.amount, tax.name or '',)

                items += """
                    <ChargesAllowances>
                      <AllowChrgIndicator></AllowChrgIndicator>
                      <AllowChrgCode></AllowChrgCode>
                      <AllowChrgAgencyCode></AllowChrgAgencyCode>
                      <AllowChrgAgency></AllowChrgAgency>
                      <AllowChrgAmt></AllowChrgAmt>
                      <AllowChrgPercentQual></AllowChrgPercentQual>
                      <AllowChrgPercent></AllowChrgPercent>
                      <PercentDollarBasis></PercentDollarBasis>
                      <AllowChrgRate></AllowChrgRate>
                      <AllowChrgQtyUOM></AllowChrgQtyUOM>
                      <AllowChrgQty></AllowChrgQty>
                      <AllowChrgHandlingCode></AllowChrgHandlingCode>
                      <ReferenceIdentification></ReferenceIdentification>
                      <AllowChrgHandlingDescription></AllowChrgHandlingDescription>
                      <OptionNumber></OptionNumber>
                      <ExceptionNumber></ExceptionNumber>
                      <AllowChrgQty2></AllowChrgQty2>
                      <LanguageCode></LanguageCode>
                      <CalculationSequence></CalculationSequence>
                      <Taxes>
                        <TaxTypeCode></TaxTypeCode>
                        <TaxAmount></TaxAmount>
                        <TaxPercentQual></TaxPercentQual>
                        <TaxPercent></TaxPercent>
                        <JurisdictionQual></JurisdictionQual>
                        <JurisdictionCode></JurisdictionCode>
                        <TaxExemptCode></TaxExemptCode>
                        <RelationshipCode></RelationshipCode>
                        <PercentDollarBasis></PercentDollarBasis>
                        <TaxHandlingCode></TaxHandlingCode>
                        <TaxID></TaxID>
                        <AssignedID></AssignedID>
                        <Description></Description>
                      </Taxes>
                    </ChargesAllowances>
                            """

                items += """
                 <Address>
                      <AddressTypeCode></AddressTypeCode>
                      <LocationCodeQualifier></LocationCodeQualifier>
                      <AddressLocationNumber></AddressLocationNumber>
                      <AddressName></AddressName>
                      <AddressAlternateName></AddressAlternateName>
                      <AddressAlternateName2></AddressAlternateName2>
                      <Address1></Address1>
                      <Address2></Address2>
                      <Address3></Address3>
                      <Address4></Address4>
                      <City></City>
                      <State></State>
                      <PostalCode></PostalCode>
                      <Country></Country>
                      <LocationID></LocationID>
                      <CountrySubDivision></CountrySubDivision>
                      <AddressTaxIdNumber></AddressTaxIdNumber>
                      <AddressTaxExemptNumber></AddressTaxExemptNumber>
                      <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                        <Description></Description>
                        <Date></Date>
                        <Time></Time>
                        <ReferenceIDs>
                          <ReferenceQual></ReferenceQual>
                          <ReferenceID></ReferenceID>
                        </ReferenceIDs>
                      </References>
                      <Contacts>
                        <ContactTypeCode></ContactTypeCode>
                        <ContactName></ContactName>
                        <PrimaryPhone></PrimaryPhone>
                        <PrimaryFax></PrimaryFax>
                        <PrimaryEmail></PrimaryEmail>
                        <AdditionalContactDetails>
                          <ContactQual></ContactQual>
                          <ContactID></ContactID>
                        </AdditionalContactDetails>
                        <ContactReference></ContactReference>
                      </Contacts>
                      <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                        <Time></Time>
                        <DateTimePeriod></DateTimePeriod>
                      </Dates>
                    </Address>
                """

                items += """
                 <Commodity>
                  <CommodityCodeQualifier></CommodityCodeQualifier>
                  <CommodityCode></CommodityCode>
                </Commodity>
                <RegulatoryCompliances>
                  <RegulatoryComplianceQual></RegulatoryComplianceQual>
                  <YesOrNoResponse></YesOrNoResponse>
                  <RegulatoryComplianceID></RegulatoryComplianceID>
                  <RegulatoryAgency></RegulatoryAgency>
                  <Description></Description>
                </RegulatoryCompliances>
                """

                items += """</Subline>
                """

                items += """
                <QuantitiesSchedulesLocations>
                <QuantityQualifier></QuantityQualifier>
                <TotalQty></TotalQty>
                <TotalQtyUOM></TotalQtyUOM>
                <QuantityDescription></QuantityDescription>
                <LocationCodeQualifier></LocationCodeQualifier>
                <LocationDescription></LocationDescription>
                <LocationQuantity>
                  <Location></Location>
                  <Qty></Qty>
                </LocationQuantity>
                <Dates>
                  <DateTimeQualifier></DateTimeQualifier>
                  <Date></Date>
                  <Time></Time>
                  <DateTimePeriod></DateTimePeriod>
                </Dates>
                <AssignedID></AssignedID>
                <LeadTimeCode></LeadTimeCode>
                <LeadTimeQuantity></LeadTimeQuantity>
                <LeadTimePeriodInterval></LeadTimePeriodInterval>
                <LeadTimeDate></LeadTimeDate>
              </QuantitiesSchedulesLocations>
                """

                items += """
                     <Taxes>
                        <TaxTypeCode></TaxTypeCode>
                        <TaxAmount></TaxAmount>
                        <TaxPercentQual></TaxPercentQual>
                        <TaxPercent></TaxPercent>
                        <JurisdictionQual></JurisdictionQual>
                        <JurisdictionCode></JurisdictionCode>
                        <TaxExemptCode></TaxExemptCode>
                        <RelationshipCode></RelationshipCode>
                        <PercentDollarBasis></PercentDollarBasis>
                        <TaxHandlingCode></TaxHandlingCode>
                        <TaxID></TaxID>
                        <AssignedID></AssignedID>
                        <Description></Description>
                    </Taxes>
                """
                items += """
                
                <ChargesAllowances>
                    <AllowChrgIndicator></AllowChrgIndicator>
                    <AllowChrgCode></AllowChrgCode>
                    <AllowChrgAgencyCode></AllowChrgAgencyCode>
                    <AllowChrgAgency></AllowChrgAgency>
                    <AllowChrgAmt></AllowChrgAmt>
                    <AllowChrgPercentQual></AllowChrgPercentQual>
                    <AllowChrgPercent></AllowChrgPercent>
                    <PercentDollarBasis></PercentDollarBasis>
                    <AllowChrgRate></AllowChrgRate>
                    <AllowChrgQtyUOM></AllowChrgQtyUOM>
                    <AllowChrgQty></AllowChrgQty>
                    <AllowChrgHandlingCode></AllowChrgHandlingCode>
                    <ReferenceIdentification></ReferenceIdentification>
                    <AllowChrgHandlingDescription></AllowChrgHandlingDescription>
                    <OptionNumber></OptionNumber>
                    <ExceptionNumber></ExceptionNumber>
                    <AllowChrgQty2></AllowChrgQty2>
                    <LanguageCode></LanguageCode>
                    <CalculationSequence></CalculationSequence>
                    <Taxes>
                      <TaxTypeCode></TaxTypeCode>
                      <TaxAmount></TaxAmount>
                      <TaxPercentQual></TaxPercentQual>
                      <TaxPercent></TaxPercent>
                      <JurisdictionQual></JurisdictionQual>
                      <JurisdictionCode></JurisdictionCode>
                      <TaxExemptCode></TaxExemptCode>
                      <RelationshipCode></RelationshipCode>
                      <PercentDollarBasis></PercentDollarBasis>
                      <TaxHandlingCode></TaxHandlingCode>
                      <TaxID></TaxID>
                      <AssignedID></AssignedID>
                      <Description></Description>
                    </Taxes>
                </ChargesAllowances>
                """

                items += """
                <FOBRelatedInstruction>
                    <FOBPayCode></FOBPayCode>
                    <FOBLocationQualifier></FOBLocationQualifier>
                    <FOBLocationDescription></FOBLocationDescription>
                    <FOBTitlePassageCode></FOBTitlePassageCode>
                    <FOBTitlePassageLocation></FOBTitlePassageLocation>
                    <TransportationTermsType></TransportationTermsType>
                    <TransportationTerms></TransportationTerms>
                    <RiskOfLossCode></RiskOfLossCode>
                    <Description></Description>
                </FOBRelatedInstruction>
                """

                items += """
                    <CarrierInformation>
                    <StatusCode></StatusCode>
                    <CarrierTransMethodCode></CarrierTransMethodCode>
                    <CarrierAlphaCode></CarrierAlphaCode>
                    <CarrierRouting></CarrierRouting>
                    <EquipmentDescriptionCode></EquipmentDescriptionCode>
                    <CarrierEquipmentInitial></CarrierEquipmentInitial>
                    <CarrierEquipmentNumber></CarrierEquipmentNumber>
                    <EquipmentType></EquipmentType>
                    <OwnershipCode></OwnershipCode>
                    <RoutingSequenceCode></RoutingSequenceCode>
                    <TransitDirectionCode></TransitDirectionCode>
                    <TransitTimeQual></TransitTimeQual>
                    <TransitTime></TransitTime>
                    <ServiceLevelCodes>
                      <ServiceLevelCode></ServiceLevelCode>
                    </ServiceLevelCodes>
                    <Address>
                      <AddressTypeCode></AddressTypeCode>
                      <LocationCodeQualifier></LocationCodeQualifier>
                      <AddressLocationNumber></AddressLocationNumber>
                      <AddressName></AddressName>
                      <AddressAlternateName></AddressAlternateName>
                      <AddressAlternateName2></AddressAlternateName2>
                      <Address1></Address1>
                      <Address2></Address2>
                      <Address3></Address3>
                      <Address4></Address4>
                      <City></City>
                      <State></State>
                      <PostalCode></PostalCode>
                      <Country></Country>
                      <LocationID></LocationID>
                      <CountrySubDivision></CountrySubDivision>
                      <AddressTaxIdNumber></AddressTaxIdNumber>
                      <AddressTaxExemptNumber></AddressTaxExemptNumber>
                      <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                        <Time></Time>
                        <DateTimePeriod></DateTimePeriod>
                      </Dates>
                    </Address>
                    <SealNumbers>
                      <SealStatusCode></SealStatusCode>
                      <SealNumber></SealNumber>
                    </SealNumbers>
                  </CarrierInformation>
                """

                items += """
                <RegulatoryCompliances>
                <RegulatoryComplianceQual></RegulatoryComplianceQual>
                <YesOrNoResponse></YesOrNoResponse>
                <RegulatoryComplianceID></RegulatoryComplianceID>
                <RegulatoryAgency></RegulatoryAgency>
                <Description></Description>
                </RegulatoryCompliances>
                """
                items += """</LineItem>
                        """
            items += """
                <Summary>
                    <TotalAmount>%s</TotalAmount>
                    <TotalLineItemNumber>%s</TotalLineItemNumber>
                    <Description>%s</Description>
                </Summary>
                """ % (record.amount_total, record.edi_total_line_number or '', record.note or '')

            items += """</Order> 
            """

        items += """</Orders>
                """
        return items

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Dev Rajan

    #////////////////////////////////////// Cross Dock

    def crossdock_generate_header_xml(self):
        header_xml = f"""<Header>
                <OrderHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <PurchaseOrderNumber>{self.edi_order_number}</PurchaseOrderNumber>
                    <TsetPurposeCode>{self.edi_tset_purpose_code}</TsetPurposeCode>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date()}</PurchaseOrderDate>
                    <AcknowledgementType></AcknowledgementType>
                    <AcknowledgementDate></AcknowledgementDate>
                    <BuyersCurrency></BuyersCurrency>
                    <Department></Department>
                    <Vendor></Vendor>
                </OrderHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
                <Time></Time>
            </Dates>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.partner_invoice_id.name}</AddressName>
                <AddressAlternateName></AddressAlternateName>
                <Address1>{self.partner_invoice_id.street or ''}</Address1>
                <Address2>{self.partner_invoice_id.street2 or ''}</Address2>
                <City>{self.partner_invoice_id.city} or ''</City>
                <State>{self.partner_invoice_id.state_id.code or ''}</State>
                <PostalCode>{self.partner_invoice_id.zip or ''}</PostalCode>
                <Country>{self.partner_invoice_id.country_id.code or ''}</Country>
            </Address>
            <Address>
                <AddressTypeCode>{'Z7'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
            </Address>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
        </Header>"""
        return header_xml

    def crossdock_generate_lineitem_xml(self):
        line_data = f""
        for line in self.order_line:
            line_data += f"""<LineItem>
            <OrderLine>
                <LineSequenceNumber>{line.line_sequence_number}</LineSequenceNumber>
                <BuyerPartNumber>{line.s_edi_vendor_prod_code}</BuyerPartNumber>
                <VendorPartNumber></VendorPartNumber>
                <ConsumerPackageCode>{line.product_id.barcode}</ConsumerPackageCode>
                <GTIN></GTIN>
                <UPCCaseCode></UPCCaseCode>
                <OrderQty>{line.edi_order_quantity}</OrderQty>
                <OrderQtyUOM>{line.product_uom.name}</OrderQtyUOM>
                <PurchasePrice>{line.price_unit}</PurchasePrice>
            </OrderLine>
            <LineItemAcknowledgement>
                <ItemStatusCode>{'IA'}</ItemStatusCode>
                <ItemScheduleQty>{line.product_uom_qty}</ItemScheduleQty>
                <ItemScheduleUOM>{line.product_uom.display_name}</ItemScheduleUOM>
                <ItemScheduleQualifier></ItemScheduleQualifier>
                <ItemScheduleDate></ItemScheduleDate>
            </LineItemAcknowledgement>
            <PriceInformation>
                <PriceTypeIDCode></PriceTypeIDCode>
                <UnitPrice></UnitPrice>
            </PriceInformation>
            <ProductOrItemDescription>
                <ProductCharacteristicCode></ProductCharacteristicCode>
                <ProductDescription></ProductDescription>
            </ProductOrItemDescription>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
            </References>
            <Notes>
                <NoteCode>{'GEN'}</NoteCode>
                <Note>{self.note or ''}</Note>
            </Notes>
        </LineItem>"""
        return line_data

    def crossdock_generate_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalAmount>{self.amount_total}</TotalAmount>
            <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def crossdock_generate_xml(self):
      for rec in self:
          data_xml = f"""<OrderAck>
              {rec.crossdock_generate_header_xml()}
              {rec.crossdock_generate_lineitem_xml()}
              {rec.crossdock_generate_summary_xml()}
       </OrderAck>"""
                      
          return data_xml
    
    #////////////////////////////////////// MultiStore
    def multistore_generate_header_xml(self):
        header_xml = f"""<Header>
                <OrderHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <PurchaseOrderNumber>{self.edi_order_number}</PurchaseOrderNumber>
                    <TsetPurposeCode>{self.edi_tset_purpose_code}</TsetPurposeCode>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date()}</PurchaseOrderDate>
                    <AcknowledgementType></AcknowledgementType>
                    <AcknowledgementDate></AcknowledgementDate>
                    <BuyersCurrency></BuyersCurrency>
                    <Department></Department>
                    <Vendor></Vendor>
                </OrderHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
                <Time></Time>
            </Dates>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.partner_invoice_id.name}</AddressName>
                <Address1>{self.partner_invoice_id.street  or ''}</Address1>
                <Address2>{self.partner_invoice_id.street2  or ''}</Address2>
                <City>{self.partner_invoice_id.city  or ''}</City>
                <State>{self.partner_invoice_id.state_id.code  or ''}</State>
                <PostalCode>{self.partner_invoice_id.zip  or ''}</PostalCode>
                <Country>{self.partner_invoice_id.country_id.code or ''}</Country>
            </Address>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
        </Header>"""
        return header_xml

    def multistore_generate_lineitem_xml(self):
        line_data = f""
        for line in self.order_line:
            line_data += f"""<LineItem>
            <OrderLine>
                <LineSequenceNumber>{line.line_sequence_number}</LineSequenceNumber>
                <BuyerPartNumber>{line.s_edi_vendor_prod_code}</BuyerPartNumber>
                <VendorPartNumber></VendorPartNumber>
                <ConsumerPackageCode>{line.product_id.barcode}</ConsumerPackageCode>
                <GTIN></GTIN>
                <UPCCaseCode></UPCCaseCode>
                <OrderQty>{line.edi_order_quantity}</OrderQty>
                <OrderQtyUOM>{line.product_uom.name}</OrderQtyUOM>
                <PurchasePrice>{line.price_unit}</PurchasePrice>
            </OrderLine>
            <LineItemAcknowledgement>
                <ItemStatusCode>{'IA'}</ItemStatusCode>
                <ItemScheduleQty>{line.product_uom_qty}</ItemScheduleQty>
                <ItemScheduleUOM>{line.product_uom.display_name}</ItemScheduleUOM>
                <ItemScheduleQualifier></ItemScheduleQualifier>
                <ItemScheduleDate></ItemScheduleDate>
            </LineItemAcknowledgement>
            <PriceInformation>
                <PriceTypeIDCode></PriceTypeIDCode>
                <UnitPrice></UnitPrice>
            </PriceInformation>
            <ProductOrItemDescription>
                <ProductCharacteristicCode></ProductCharacteristicCode>
                <ProductDescription></ProductDescription>
            </ProductOrItemDescription>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
            </References>
            <Notes>
                <NoteCode>{'GEN'}</NoteCode>
                <Note>{self.note or ''}</Note>
            </Notes>
        </LineItem>"""
        return line_data

    def multistore_generate_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalAmount>{self.amount_total}</TotalAmount>
            <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def multistore_generate_xml(self):
      for rec in self:
          data_xml = f"""<OrderAck>
              {rec.multistore_generate_header_xml()}
              {rec.multistore_generate_lineitem_xml()}
              {rec.multistore_generate_summary_xml()}
       </OrderAck>"""
          return data_xml

    #////////////////////////////////////// BulkImport
    def blkimport_generate_header_xml(self):
        header_xml = f"""<Header>
                <OrderHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <PurchaseOrderNumber>{self.edi_order_number}</PurchaseOrderNumber>
                    <TsetPurposeCode>{self.edi_tset_purpose_code}</TsetPurposeCode>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date()}</PurchaseOrderDate>
                    <AcknowledgementType></AcknowledgementType>
                    <AcknowledgementDate></AcknowledgementDate>
                    <BuyersCurrency></BuyersCurrency>
                    <Department></Department>
                    <Vendor></Vendor>
                </OrderHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
                <Time></Time>
            </Dates>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.partner_invoice_id.name}</AddressName>
                <Address1>{self.partner_invoice_id.street  or ''}</Address1>
                <Address2>{self.partner_invoice_id.street2  or ''}</Address2>
                <City>{self.partner_invoice_id.city  or ''}</City>
                <State>{self.partner_invoice_id.state_id.code  or ''}</State>
                <PostalCode>{self.partner_invoice_id.zip  or ''}</PostalCode>
                <Country>{self.partner_invoice_id.country_id.code or ''}</Country>
            </Address>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
        </Header>"""
        return header_xml

    def blkimport_generate_lineitem_xml(self):
        line_data = f""
        for line in self.order_line:
            line_data += f"""<LineItem>
            <OrderLine>
                <LineSequenceNumber>{line.line_sequence_number}</LineSequenceNumber>
                <BuyerPartNumber>{line.s_edi_vendor_prod_code}</BuyerPartNumber>
                <VendorPartNumber></VendorPartNumber>
                <ConsumerPackageCode>{line.product_id.barcode}</ConsumerPackageCode>
                <GTIN></GTIN>
                <UPCCaseCode></UPCCaseCode>
                <OrderQty>{line.edi_order_quantity}</OrderQty>
                <OrderQtyUOM>{line.product_uom.name}</OrderQtyUOM>
                <PurchasePrice>{line.price_unit}</PurchasePrice>
            </OrderLine>
            <LineItemAcknowledgement>
                <ItemStatusCode>{'IA'}</ItemStatusCode>
                <ItemScheduleQty>{line.product_uom_qty}</ItemScheduleQty>
                <ItemScheduleUOM>{line.product_uom.display_name}</ItemScheduleUOM>
                <ItemScheduleQualifier></ItemScheduleQualifier>
                <ItemScheduleDate></ItemScheduleDate>
            </LineItemAcknowledgement>
            <PriceInformation>
                <PriceTypeIDCode></PriceTypeIDCode>
                <UnitPrice></UnitPrice>
            </PriceInformation>
            <ProductOrItemDescription>
                <ProductCharacteristicCode></ProductCharacteristicCode>
                <ProductDescription></ProductDescription>
            </ProductOrItemDescription>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
            </References>
            <Notes>
                <NoteCode>{'GEN'}</NoteCode>
                <Note>{self.note or ''}</Note>
            </Notes>
        </LineItem>"""
        return line_data

    def blkimport_generate_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalAmount>{self.amount_total}</TotalAmount>
            <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def blkimport_generate_xml(self):
      for rec in self:
          data_xml = f"""<OrderAck>
              {rec.blkimport_generate_header_xml()}
              {rec.blkimport_generate_lineitem_xml()}
              {rec.blkimport_generate_summary_xml()}
       </OrderAck>"""
          return data_xml

    #////////////////////////////////////// DropShip
    def dropship_generate_header_xml(self):
        reference_qual = ''
        edi_ref_id = ''
        for record in self:
            reference_qual = [edi_ref.edi_ref_qual for edi_ref in record.edi_reference_ids]
            edi_ref_id = [edi_ref.edi_ref_id for edi_ref in record.edi_reference_ids]
        current_date = datetime.now().date()
        header_xml = f"""<Header>
                <OrderHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <PurchaseOrderNumber>{self.edi_order_number}</PurchaseOrderNumber>
                    <TsetPurposeCode>{self.edi_tset_purpose_code}</TsetPurposeCode>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date()}</PurchaseOrderDate>
                    <AcknowledgementNumber>{self.edi_acknowledment_num}</AcknowledgementNumber>
                    <AcknowledgementType>{'AC'}</AcknowledgementType>
                    <AcknowledgementDate>{current_date}</AcknowledgementDate>
                    <BuyersCurrency></BuyersCurrency>
                    <Department></Department>
                    <Vendor>{self.edi_vendor_number}</Vendor>
                    <customerordernumber>{self.name}</customerordernumber>
                </OrderHeader>
            <Dates>
                <DateTimeQualifier>{self.edi_date_type}</DateTimeQualifier>
                <Date>{current_date}</Date>
                <Time></Time>
            </Dates>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier>{self.edi_st_loc_code_qualifier}</LocationCodeQualifier>
                <AddressLocationNumber>{self.edi_st_addr_loc_number}</AddressLocationNumber>
                <AddressName>{self.partner_invoice_id.name}</AddressName>
                <AddressAlternateName></AddressAlternateName>
                <Address1>{self.partner_invoice_id.street or ''}</Address1>
                <Address2>{self.partner_invoice_id.street2 or ''}</Address2>
                <City>{self.partner_invoice_id.city} or ''</City>
                <State>{self.partner_invoice_id.state_id.code or ''}</State>
                <PostalCode>{self.partner_invoice_id.zip or ''}</PostalCode>
                <Country>{self.partner_invoice_id.country_id.code or ''}</Country>
            </Address>
            <References>
                <ReferenceQual>{reference_qual}</ReferenceQual>
                <ReferenceID>{edi_ref_id}</ReferenceID>
                <Description></Description>
            </References>
            <QuantityAndWeight>
                <PackingMedium></PackingMedium>
                <LadingQuantity></LadingQuantity>
                <Weight></Weight>
                <WeightUOM></WeightUOM>                
            </QuantityAndWeight>
            
        </Header>"""
        return header_xml

    def dropship_generate_lineitem_xml(self):
        reference_qual = ''
        edi_ref_id = ''
        for record in self:
            reference_qual = [edi_ref.edi_ref_qual for edi_ref in record.edi_reference_ids]
            edi_ref_id = [edi_ref.edi_ref_id for edi_ref in record.edi_reference_ids]
        current_date = datetime.now().date()
        line_data = f""
        for line in self.order_line:
            line_data += f"""<LineItem>
            <OrderLine>
                <LineSequenceNumber>{line.line_sequence_number}</LineSequenceNumber>
                <BuyerPartNumber>{line.s_edi_vendor_prod_code}</BuyerPartNumber>
                <VendorPartNumber>{line.product_id.default_code}</VendorPartNumber>
                <ConsumerPackageCode>{line.product_id.barcode}</ConsumerPackageCode>
                <GTIN></GTIN>
                <UPCCaseCode></UPCCaseCode>
                <ProductID>
                    <OrderQty>{line.edi_order_quantity}</OrderQty>
                    <OrderQtyUOM>{line.product_uom.name}</OrderQtyUOM>
                    <PurchasePrice>{line.price_unit}</PurchasePrice>
                </ProductID>
            </OrderLine>
            <LineItemAcknowledgement>
                <LineSequenceNumber>{line.line_sequence_number}</LineSequenceNumber>
                <ItemStatusCode>{'AR'}</ItemStatusCode>
                <ItemScheduleQty>{line.product_uom_qty}</ItemScheduleQty>
                <ItemScheduleUOM>{line.product_uom.display_name}</ItemScheduleUOM>
                <ItemScheduleQualifier>{'017'}</ItemScheduleQualifier>
                <ItemScheduleDate>{current_date}</ItemScheduleDate>
            </LineItemAcknowledgement>
            <Dates>
                <DateTimeQualifier>{self.edi_date_type}</DateTimeQualifier>
                <Date>{current_date}</Date>
            </Dates>
            <PriceInformation>
                <PriceTypeIDCode></PriceTypeIDCode>
                <UnitPrice></UnitPrice>
                <PriceMultiplier></PriceMultiplier>
                <Quantity></Quantity>
                <QuantityUOM></QuantityUOM>
            </PriceInformation>
            <References>
                <ReferenceQual>{reference_qual}</ReferenceQual>
                <ReferenceID>{edi_ref_id}</ReferenceID>
            </References>
            <Notes>
                <NoteCode>{'GEN'}</NoteCode>
                <Note>{self.note or ''}</Note>
            </Notes>
        </LineItem>"""
        return line_data

    def dropship_generate_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalAmount>{self.amount_total}</TotalAmount>
            <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def dropship_generate_xml(self):
      for rec in self:
          data_xml = f"""<OrderAck>
              {rec.dropship_generate_header_xml()}
              {rec.dropship_generate_lineitem_xml()}
              {rec.dropship_generate_summary_xml()}
       </OrderAck>"""
                      
          return data_xml

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def create_855_ack_queue(self):
        try:
            filename = 'PR_' + str(datetime.now().strftime("%d_%m_%Y_%H_%M_%S"))
            file_path = os.path.join(
                self.edi_outbound_file_path, '%s.xml' % filename)
            # data_xml = self.prepare_sale_order_xml()
            # data_xml = rec.crossdock_generate_xml()
            # data_xml = rec.multistore_generate_xml()
            # data_xml = rec.blkimport_generate_xml()
            data_xml = self.dropship_generate_xml()
            # ==========================

            # Create attachment to link wit SaleOrder
            self.env['ir.attachment'].create({
                'name': f'{filename}.xml',
                'res_id': self.id,
                'res_model': 'sale.order',
                'datas': base64.encodebytes(bytes(data_xml, 'utf-8')),
                'mimetype': 'application/xml',
            })

            if self.edi_config_id and file_path and data_xml:
                dq_id = self.env['order.ack.data.queue'].create({
                    'edi_config_id': self.edi_config_id.id,
                    'edi_order': self.edi_order_number,
                    'so_order_id': self.id,
                    'path': file_path,
                    'edi_order_data': data_xml,
                })
                self.update({'edi_order_ack_dq_id': dq_id})
                dq_id.export_data()

        except Exception as e:
            raise ValidationError(_(e))


    def check_trading_partner_field(self, edi_order_data, trading_partner_field_ids):
        """Fetch the value from Partner SPS Field and raise a warning if the required tag value is not in XML."""
        missing_fields = set()

        for record in trading_partner_field_ids.filtered(lambda a:a.document_type=='order_ack'):
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

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for rec in self:
            if rec.edi_config_id:
                data_xml = self.dropship_generate_xml()
                # ==========================
                partner_env = self.env['res.partner']
                DOMTree = xml.dom.minidom.parseString(data_xml)
                edi_order_data = DOMTree.documentElement
                trading_partner_id = edi_order_data.getElementsByTagName("TradingPartnerId")[0].firstChild.data
                if trading_partner_id:
                    partner = partner_env.search(
                        [('trading_partner_id', '=', trading_partner_id)], limit=1)
                    if not partner:
                        raise ValidationError(_("Trading Partner not defined in Odoo System for record"))
                else:
                    raise ValidationError(_("Trading Partner ID missing in XML file. for record"))
                self.check_trading_partner_field(edi_order_data, partner.trading_partner_field_ids)

                if rec.partner_invoice_id.edi_855 and rec.edi_outbound_file_path:
                    self.edi_acknowledment_num = self.env['ir.sequence'].next_by_code(
                        'sale.order1')
                    rec.with_delay(description="Creating 855 Data Queue for Sale order - %s" % rec.name, max_retries=5).create_855_ack_queue()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    s_edi_vendor_prod_code = fields.Char(string="EDI Vendor Product Code")
    edi_order_quantity = fields.Float(string='EDI Quantity', readonly=True)
    line_sequence_number = fields.Char(string="Line Sequence Number", readonly=True)
    edi_vendor_part_number = fields.Char(string="Vendor Part Number", readonly=True)
    edi_upc_case_code = fields.Char(string="EDI UPCCaseCode", readonly=True)
    edi_delivery_date = fields.Datetime(string="EDI Requested Delivery Date", readonly=True)
    edi_latest_ship_date = fields.Datetime(string="EDI Latest Ship Date", readonly=True)
    edi_qty_schedule_location = fields.Char(string="EDI QuantitiesSchedulesLocation", readonly=True)
    edi_line_note_code = fields.Char('EDI Line NoteCode', readonly=True)
    edi_line_note = fields.Char('EDI Line Note', readonly=True)
    pricelist_price = fields.Float(string="Subtotal Untax")

    def _check_line_unlink(self):
        if self.order_id.edi_config_id:
            return self.filtered(lambda line: (
                    line.invoice_lines or not line.is_downpayment))
        else:
            return self.filtered(
                lambda line: line.state in ('sale', 'done') and (line.invoice_lines or not line.is_downpayment))

    def unlink(self):
        if self.order_id.edi_config_id:
            raise UserError(_('You can not remove an order line from the EDI Sales Order.\n'
                              'You should rather set the quantity to 0.'))
        return super(SaleOrderLine, self).unlink()

    def _compute_line_pricelist_price(self):
        """
        Define the function to calculate the pricelist price based on the
        pricelist selection on the EDI Order.
        @return:
        @rtype:
        """
        for line in self:
            pricelist_price = 0.0
            line = line.with_company(line.company_id)
            if line.pricelist_item_id:
                price = line._get_display_price()
                pricelist_price = price
            subtotal_untax = line.product_uom_qty * pricelist_price
            line.update({'pricelist_price': subtotal_untax})


class EDIOrderReference(models.Model):
    _name = "edi.order.reference"
    _description = "Edi Order References"
    _rec_name = "edi_ref_qual"

    sale_id = fields.Many2one('sale.order', string="Sale Order")
    edi_ref_qual = fields.Char(string="EDI ReferenceQual", readonly=True)
    edi_ref_id = fields.Char(string="EDI ReferenceID", readonly=True)
    edi_ref_description = fields.Char(string="EDI Description", readonly=True)
