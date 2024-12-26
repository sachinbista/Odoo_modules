# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

import os
import base64

from datetime import datetime
import xml.dom.minidom

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError,UserError


class AccountInvoice(models.Model):
    _inherit = "account.move"

    def _compute_810_rec_count(self):
        for pick in self:
            rec_810_count = self.env['invoice.data.queue'].search([('move_id', '=', pick.id)])
            pick.rec_810_count = len(rec_810_count.ids)

    edi_config_id = fields.Many2one(
        'edi.config', string='EDI Config', readonly=True)
    edi_outbound_file_path = fields.Char(
        string="Outbound File path", readonly=True)
    edi_order_number = fields.Char(string="EDI Order Number", readonly=True)
    edi_order_date = fields.Datetime(string="EDI Order Date", readonly=True)
    edi_trading_partner_id = fields.Char(
        string="Trading Partner ID", readonly=True)
    edi_invoice_dq_id = fields.Many2one(
        'invoice.data.queue', string="Invoice Data Queue")
    edi_vendor_number = fields.Char(string="Vendor", readonly=True)
    edi_bt_addr_loc_number = fields.Char(string="BT-Address Location Number", readonly=True)
    edi_bt_loc_code_qualifier = fields.Char(string="BT-Location Code Qualifier", readonly=True)
    edi_st_addr_loc_number = fields.Char(string="ST-Address Location Number", readonly=True)
    edi_st_loc_code_qualifier = fields.Char(string="ST-Location Code Qualifier", readonly=True)
    edi_total_line_number = fields.Char(string="Total Line Number", readonly=True)
    edi_tset_purpose_code = fields.Char(string="Tset Purpose Code", readonly=True)
    rec_810_count = fields.Integer(string='Delivery Orders', compute='_compute_810_rec_count')

    def action_view_810_records(self):
        self.ensure_one()
        rec_810_count = self.env['invoice.data.queue'].search([('move_id', '=', self.id)])
        action = self.env["ir.actions.actions"]._for_xml_id("bista_sps_connector.edi_config_invoice_data_queue")

        if len(rec_810_count) > 1:
            action['domain'] = [('id', 'in', rec_810_count.ids)]
        elif rec_810_count:
            form_view = [(self.env.ref('bista_sps_connector.edi_configuration_invoice_data_queue_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = rec_810_count.id
        return action

    @api.model
    def create(self, vals):
        """
        This function is to update edi_config value on creation
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        res = super(AccountInvoice, self).create(vals)
        partner_id = self.env['res.partner'].browse(vals.get('partner_id'))
        for record in res:
            if 'partner_id' in vals:
                record.update({
                    'edi_config_id': partner_id.edi_config_id,
                    'edi_outbound_file_path': partner_id.edi_outbound_file_path
                })
        return res

    def write(self, vals):
        """
        This function is to update edi_config value
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        res = super(AccountInvoice, self).write(vals)
        if 'partner_id' in vals:
            partner_id = self.env['res.partner'].browse(vals.get('partner_id'))
            for record in self:
                record.update({
                    'edi_config_id': partner_id.edi_config_id,
                    'edi_outbound_file_path': partner_id.edi_outbound_file_path
                })
        return res

    def carrier_details(self, invoice):
        return """
                  <References>
                    <ReferenceQual></ReferenceQual>
                    <ReferenceID></ReferenceID>
                    <Description></Description>
                  </References>
                  """

    def prepare_invoices_xml(self):
        """
        This function is used to prepare xml document with invoice values
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        items = """<Invoices>
                """
        for invoice in self:
            items += """<Invoice>
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
                </Meta>
            """

            items += """<Header>
            """

            items += """
                <InvoiceHeader>
                    <TradingPartnerId>%s</TradingPartnerId>
                    <InvoiceNumber>%s</InvoiceNumber>
                    <InvoiceDate>%s</InvoiceDate>
                    <PurchaseOrderDate>%s</PurchaseOrderDate>
                    <PurchaseOrderNumber>%s</PurchaseOrderNumber>
                    <TsetPurposeCode>%s</TsetPurposeCode>
                    <BuyersCurrency></BuyersCurrency>
                    <Vendor>%s</Vendor>
                  </InvoiceHeader>
            """ % (invoice.edi_trading_partner_id, invoice.name, invoice.invoice_date, invoice.edi_order_date.date() or '',
                   invoice.edi_order_number or '', invoice.edi_tset_purpose_code or '', invoice.edi_vendor_number or ''
                   )

            for payment in invoice.invoice_payment_term_id:
                payment_term_name = payment.name
                payment_description = payment.note
                pt_discount_percentage = 0
                pt_discount_days = 0
                pt_net_days = 0
                pt_discount_amount = ''
                pt_type = ''
                pt_options = ''
                for pt_line in payment.line_ids:
                    pt_type = pt_line.value
                    if pt_type == 'balance':
                        pt_discount_percentage = pt_line.value_amount
                        # pt_discount_days = pt_line.discount_applicable_on_days
                        pt_net_days = pt_line.days or ''
                        # pt_options = pt_line.option or ''

                    elif pt_type == 'percent':
                        pt_discount_percentage = pt_line.value_amount
                        # pt_discount_days = pt_line.discount_applicable_on_days
                        pt_net_days = pt_line.days or ''
                        # pt_options = pt_line.option or ''

                    elif pt_type == 'fixed':
                        pt_discount_amount = pt_line.value_amount or ''
                        # pt_discount_days = pt_line.discount_applicable_on_days
                        pt_net_days = pt_line.days or ''
                        # pt_options = pt_line.option or ''
                    break

                items += """
                    <PaymentTerms>
                                <TermsType>01</TermsType>
                                <TermsDiscountPercentage>%s</TermsDiscountPercentage>
                                <TermsDiscountDueDays>%s</TermsDiscountDueDays>
                                <TermsNetDueDays>%s</TermsNetDueDays>
                                <TermsDiscountAmount>%s</TermsDiscountAmount>
                                <TermsDescription>%s</TermsDescription>
                            </PaymentTerms>
                """ % (pt_discount_percentage, pt_discount_days, pt_net_days, pt_discount_amount,
                       payment_description or '')

            items += """
                    <Dates>
                <DateTimeQualifier>001</DateTimeQualifier>
                <Date>%s</Date>
              </Dates>
            """ % invoice.invoice_date

            items += """
                <Contacts>
                <ContactTypeCode>BD</ContactTypeCode>
                <ContactName>%s</ContactName>
                <PrimaryPhone>%s</PrimaryPhone>
                <PrimaryEmail>%s</PrimaryEmail>
                </Contacts>
            """ % (invoice.partner_id.name, invoice.partner_id.phone or '', invoice.partner_id.email)

            items += """
                 <Address>
                    <AddressTypeCode>BT</AddressTypeCode>
                    <LocationCodeQualifier>%s</LocationCodeQualifier>
                    <AddressLocationNumber>%s</AddressLocationNumber>
                    <AddressName>%s</AddressName>
                    <Address1>%s</Address1>
                    <Address2>%s</Address2>
                    <City>%s</City>
                    <State>%s</State>
                    <PostalCode>%s</PostalCode>
                    <Country>%s</Country>
                  </Address>
            """ % (invoice.edi_bt_loc_code_qualifier or '', invoice.edi_bt_addr_loc_number or '', invoice.partner_id.name,
                   invoice.partner_id.street or '', invoice.partner_id.street2 or '', invoice.partner_id.city,
                   invoice.partner_id.state_id.code, invoice.partner_id.zip, invoice.partner_id.country_id.code)
            items += """
                    <Address>
                      <AddressTypeCode>ST</AddressTypeCode>
                      <LocationCodeQualifier>%s</LocationCodeQualifier>
                      <AddressLocationNumber>%s</AddressLocationNumber>
                      <AddressName>%s</AddressName>
                      <Address1>%s</Address1>
                      <Address2>%s</Address2>
                      <City>%s</City>
                      <State>%s</State>
                      <PostalCode>%s</PostalCode>
                      <Country>%s</Country>
                    </Address>
            """ % (invoice.edi_st_loc_code_qualifier or '', invoice.edi_st_addr_loc_number or '',
                   invoice.partner_shipping_id.name or '',
                   invoice.partner_shipping_id.street or '', invoice.partner_shipping_id.street2 or '',
                   invoice.partner_shipping_id.city,
                   invoice.partner_shipping_id.state_id.code, invoice.partner_shipping_id.zip,
                   invoice.partner_shipping_id.country_id.code)
            items += """
                    <Address>
                      <AddressTypeCode>RT</AddressTypeCode>
                      <LocationCodeQualifier></LocationCodeQualifier>
                      <AddressLocationNumber></AddressLocationNumber>
                      <AddressName>%s</AddressName>
                      <Address1>%s</Address1>
                      <Address2>%s</Address2>
                      <City>%s</City>
                      <State>%s</State>
                      <PostalCode>%s</PostalCode>
                      <Country>%s</Country>
                    </Address>
            """ % (
                   invoice.company_id.name or '',
                   invoice.company_id.street or '', invoice.company_id.street2 or '',
                   invoice.company_id.city,
                   invoice.company_id.state_id.code, invoice.company_id.zip,
                   invoice.company_id.country_id.code)

            items += self.carrier_details(invoice)

            items += """
                <CarrierInformation>
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
                    <TransitTimeQualifier></TransitTimeQualifier>
                    <TransitTime></TransitTime>
                    <ServiceLevelCodes>
                      <ServiceLevelCode></ServiceLevelCode>
                    </ServiceLevelCodes>
                  </CarrierInformation>
            """

            items += """</Header>
                       """
            sale_line_ids = self.env['sale.order.line']
            # count = 0
            line_sequence_number = ''
            vendor_part_number = ''
            buyer_part_number = ''
            consumer_package_code = ''
            product_uom_qty = ''
            product_uom = ''
            ship_uom = ''
            ship_qty = 0

            for line in invoice.invoice_line_ids:
                sale_line_ids |= line.sale_line_ids
                for sale_lines in sale_line_ids:
                    line_sequence_number = sale_lines.line_sequence_number
                    vendor_part_number = sale_lines.edi_vendor_part_number or sale_lines.product_id.name or ''
                    buyer_part_number = sale_lines.s_edi_vendor_prod_code or ''
                    consumer_package_code = sale_lines.product_id.barcode or ''
                    product_uom_qty = sale_lines.product_uom_qty
                    product_uom = sale_lines.product_uom.edi_uom_code
                    # stock_move_ids = self.env['stock.move'].sudo().search(
                    #     [('sale_line_id', 'in', sale_line_ids.ids)])
                    # print("stock_move_ids-------------",stock_move_ids)
                    # # new_carrier_id_name = ''
                    # # carrier_tracking_ref = ''
                    # for stock_move in stock_move_ids:
                    #     move_lines = stock_move.picking_id.move_line_ids
                    #     print("move_line----------------",move_lines)
                    stock_move_ids = sale_lines.move_ids.filtered(
                        lambda x: x.picking_id and x.picking_id.picking_type_id
                                  and x.picking_id.picking_type_id.sequence_code == 'OUT')
                    for stock_id in stock_move_ids:
                        ship_qty = stock_id.quantity
                        ship_uom = stock_id.product_uom.name
                    # if '&' in stock_move.picking_id.carrier_id.name:
                    #     new_carrier_id_name = stock_move.picking_id.carrier_id.name.replace(' & ', ' &amp; ')
                    # else:
                    # new_carrier_id_name = stock_move.picking_id.carrier_id.name
                    # carrier_tracking_ref = stock_move.picking_id.carrier_tracking_ref
                    # for ml in move_lines:
                    #     ship_qty = ml.qty_done
                    #     ship_uom = ml.product_uom_id.uom_code
                items += """<LineItem>
                """
                # count += 1
                items += """
                     <InvoiceLine>
                        <LineSequenceNumber>%s</LineSequenceNumber>
                        <BuyerPartNumber>%s</BuyerPartNumber>
                        <VendorPartNumber>%s</VendorPartNumber>
                        <ConsumerPackageCode>%s</ConsumerPackageCode>
                        <InvoiceQty>%s</InvoiceQty>
                        <InvoiceQtyUOM>%s</InvoiceQtyUOM>
                        <OrderQty>%s</OrderQty>
                        <OrderQtyUOM>%s</OrderQtyUOM>
                        <PurchasePrice>%s</PurchasePrice>
                        <ShipQty>%s</ShipQty>
                        <ShipQtyUOM>%s</ShipQtyUOM>
                        <ExtendedItemTotal>50</ExtendedItemTotal>
                      </InvoiceLine>
                """ % (line_sequence_number, buyer_part_number, vendor_part_number, consumer_package_code,
                       line.quantity, line.product_uom_id.edi_uom_code, product_uom_qty or '',
                       product_uom or '', line.price_unit, ship_qty, ship_uom)
                # print("line.tax_ids----------------",line.tax_ids)
                # print("line.tax_ids----------------",invoice.amount_by_group)
                # print("line.tax_ids----------------",invoice.amount_by_group['tax_amount'])
                # sd
                for tax in line.tax_ids:
                    # print("tax base amount--------------",line.tax_base_amount)
                    items += """
                        <Taxes>
                        <TaxTypeCode>%s</TaxTypeCode>
                        <TaxPercent>%s</TaxPercent>
                        <Description>%s</Description>
                        </Taxes>
                    """ % (tax.tax_type_code, tax.amount, tax.name or '')
                items +="""    
                      <ProductOrItemDescription>
                        <ProductCharacteristicCode>08</ProductCharacteristicCode>
                        <ProductDescription>%s</ProductDescription>
                      </ProductOrItemDescription>
                """ % line.name or ''
            items += """</LineItem>

            """

            amount_total = invoice.amount_total
            amount_taxed = invoice.amount_tax
            items += """
             <Summary>
              <TotalAmount>%s</TotalAmount>
              <TotalSalesAmount></TotalSalesAmount>
              <TotalTaxesAndCharges>%s</TotalTaxesAndCharges>
              <TotalLineItemNumber>%s</TotalLineItemNumber>
            </Summary>
            """ % (amount_total, amount_taxed, invoice.edi_total_line_number or '')

            items += """</Invoice>
                        """

        items += """</Invoices>
                     """
        return items

     #////////////////////////////////////// INV Crossdock

    def crossdock_inv_generate_pay_term_xml(self):
        payment_items = f""""""
        for payment in self.invoice_payment_term_id:
            payment_description = payment.note
            pt_discount_percentage = 0
            pt_discount_days = 0
            pt_net_days = 0
            pt_discount_amount = ''
            pt_type = ''
            for pt_line in payment.line_ids:
                pt_type = pt_line.value
                if pt_type == 'balance':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'percent':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'fixed':
                    pt_discount_amount = pt_line.value_amount or ''
                    pt_net_days = pt_line.nb_days or ''
                break

            payment_items += f"""<PaymentTerms>
                        <TermsType>{'01'}</TermsType>
                        <TermsDiscountPercentage>{pt_discount_percentage}</TermsDiscountPercentage>
                        <TermsDiscountDueDays>{pt_discount_days}</TermsDiscountDueDays>
                        <TermsNetDueDays>{pt_net_days}</TermsNetDueDays>
                        <TermsDiscountAmount>{pt_discount_amount}</TermsDiscountAmount>
                        <TermsDescription>{ payment_description or ''}</TermsDescription>
                    </PaymentTerms>"""
        return payment_items


    def crossdock_inv_generate_header_xml(self):
        header_xml = f"""<Header>
                <InvoiceHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <InvoiceNumber>{self.name}</InvoiceNumber>
                    <InvoiceDate>{self.invoice_date or ''}</InvoiceDate>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date() or ''}</PurchaseOrderDate>
                    <PurchaseOrderNumber>{self.edi_order_number or ''}</PurchaseOrderNumber>
                    <InvoiceTypeCode>{'DR'}</InvoiceTypeCode>
                    <TsetPurposeCode>{self.edi_tset_purpose_code or ''}</TsetPurposeCode>
                    <BuyersCurrency></BuyersCurrency>
                    <Department>{'SPS'}</Department>
                    <Vendor>{self.edi_vendor_number or ''}</Vendor>
                    <BillOfLadingNumber></BillOfLadingNumber>
                    <ShipDate></ShipDate>
                </InvoiceHeader>
                {self.crossdock_inv_generate_pay_term_xml()}
                <Dates>
                    <DateTimeQualifier>{'002'}</DateTimeQualifier>
                    <Date>{self.invoice_date}</Date>
                </Dates>
                <Contacts>
                    <ContactTypeCode>IC</ContactTypeCode>
                    <ContactName>{self.partner_id.name}</ContactName>
                    <PrimaryPhone>{self.partner_id.phone or ''}</PrimaryPhone>
                    <PrimaryFax></PrimaryFax>
                    <PrimaryEmail>{self.partner_id.email}</PrimaryEmail>
                </Contacts>
                <Address>
                    <AddressTypeCode>{'BT'}</AddressTypeCode>
                    <LocationCodeQualifier>{self.edi_bt_loc_code_qualifier or ''}</LocationCodeQualifier>
                    <AddressLocationNumber>{self.edi_bt_addr_loc_number or ''}</AddressLocationNumber>
                    <AddressName>{self.partner_id.name}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.partner_id.street or ''}</Address1>
                    <Address2>{self.partner_id.street2 or ''}</Address2>
                    <City>{self.partner_id.city}</City>
                    <State>{self.partner_id.state_id.code}</State>
                    <PostalCode>{self.partner_id.zip}</PostalCode>
                    <Country>{self.partner_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>RI</AddressTypeCode>
                    <LocationCodeQualifier></LocationCodeQualifier>
                    <AddressLocationNumber></AddressLocationNumber>
                    <AddressName>{self.company_id.name or ''}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.company_id.street or ''}</Address1>
                    <Address2>{self.company_id.street2 or ''}</Address2>
                    <City>{self.company_id.city}</City>
                    <State>{self.company_id.state_id.code}</State>
                    <PostalCode>{self.company_id.zip}</PostalCode>
                    <Country>{self.company_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>{'ST'}</AddressTypeCode>
                    <LocationCodeQualifier>{self.edi_st_loc_code_qualifier or ''}</LocationCodeQualifier>
                    <AddressLocationNumber>{self.edi_st_addr_loc_number or ''}</AddressLocationNumber>
                    <AddressName>{self.partner_shipping_id.name or ''}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.partner_shipping_id.street or ''}</Address1>
                    <Address2>{self.partner_shipping_id.street2 or ''}</Address2>
                    <City>{self.partner_shipping_id.city}</City>
                    <State>{self.partner_shipping_id.state_id.code}</State>
                    <PostalCode>{self.partner_shipping_id.zip}</PostalCode>
                    <Country>{self.partner_shipping_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>Z7</AddressTypeCode>
                    <LocationCodeQualifier></LocationCodeQualifier>
                    <AddressLocationNumber></AddressLocationNumber>
                </Address>
                <References>
                    <ReferenceQual></ReferenceQual>
                    <ReferenceID></ReferenceID>
                    <Description></Description>
                </References>
                <Notes>
                    <NoteCode></NoteCode>
                    <Note></Note>
                </Notes>
                <FOBRelatedInstruction>
                    <FOBPayCode></FOBPayCode>
                    <FOBLocationQualifier></FOBLocationQualifier>
                    <FOBLocationDescription></FOBLocationDescription>
                </FOBRelatedInstruction>
                <CarrierInformation>
                    <StatusCode></StatusCode>
                    <CarrierTransMethodCode></CarrierTransMethodCode>
                    <CarrierAlphaCode></CarrierAlphaCode>
                    <CarrierRouting></CarrierRouting>
                    <EquipmentDescriptionCode></EquipmentDescriptionCode>
                    <CarrierEquipmentNumber></CarrierEquipmentNumber>
                    <SealNumbers>
                        <SealNumber></SealNumber>
                    </SealNumbers>
                </CarrierInformation>
                <QuantityTotals>
                    <QuantityTotalsQualifier>{'SQT'}</QuantityTotalsQualifier>
                    <Quantity></Quantity>
                    <QuantityUOM></QuantityUOM>
                </QuantityTotals>
            </Header>"""
        return header_xml

    def crossdock_inv_generate_lineitem_xml(self):
        line_xml= f""""""
        sale_line_ids = self.env['sale.order.line']
        line_sequence_number = ''
        vendor_part_number = ''
        buyer_part_number = ''
        consumer_package_code = ''
        product_uom_qty = ''
        product_uom = ''
        ship_uom = ''
        ship_qty = 0

        for line in self.invoice_line_ids:
            sale_line_ids |= line.sale_line_ids
            for sale_lines in sale_line_ids:
                line_sequence_number = sale_lines.line_sequence_number
                vendor_part_number = sale_lines.edi_vendor_part_number or sale_lines.product_id.name or ''
                buyer_part_number = sale_lines.s_edi_vendor_prod_code or ''
                consumer_package_code = sale_lines.product_id.barcode or ''
                product_uom_qty = sale_lines.product_uom_qty
                product_uom = sale_lines.product_uom.edi_uom_code
                stock_move_ids = sale_lines.move_ids.filtered(
                    lambda x: x.picking_id and x.picking_id.picking_type_id
                                and x.picking_id.picking_type_id.sequence_code == 'OUT')
                for stock_id in stock_move_ids:
                    ship_qty = stock_id.quantity
                    ship_uom = stock_id.product_uom.name

            line_xml += f"""<LineItem>
                    <InvoiceLine>
                        <LineSequenceNumber>{line_sequence_number}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <InvoiceQty>{line.quantity}</InvoiceQty>
                        <InvoiceQtyUOM>{line.product_uom_id.edi_uom_code}</InvoiceQtyUOM>
                        <PurchasePrice>{line.price_unit}</PurchasePrice>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_uom}</ShipQtyUOM>
                        <ExtendedItemTotal></ExtendedItemTotal>
                    </InvoiceLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode>{'08'}</ProductCharacteristicCode>
                        <ProductDescription>{line.name or ''}</ProductDescription>
                    </ProductOrItemDescription>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </LineItem>"""
        return line_xml

    def crossdock_inv_generate_summary_xml(self):
        summary_xml = f"""<Summary>
                <TotalAmount>{self.amount_total}</TotalAmount>
                <TotalSalesAmount></TotalSalesAmount>
                <TotalTermsDiscountAmount></TotalTermsDiscountAmount>
                <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
                <InvoiceAmtDueByTermsDate></InvoiceAmtDueByTermsDate>
            </Summary>"""
        return summary_xml

    def crossdock_inv_generate_xml(self):
        data_xml = f""""""
        for rec in self:
            data_xml = f"""<Invoice>
                {rec.crossdock_inv_generate_header_xml()}
                {rec.crossdock_inv_generate_lineitem_xml()}
                {rec.crossdock_inv_generate_summary_xml()}
            </Invoice>"""
        return data_xml
    
    #////////////////////////////////////// INV MultiStore

    def multistore_inv_generate_pay_term_xml(self):
        payment_items = f""""""
        for payment in self.invoice_payment_term_id:
            payment_description = payment.note
            pt_discount_percentage = 0
            pt_discount_days = 0
            pt_net_days = 0
            pt_discount_amount = ''
            pt_type = ''
            for pt_line in payment.line_ids:
                pt_type = pt_line.value
                if pt_type == 'balance':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'percent':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'fixed':
                    pt_discount_amount = pt_line.value_amount or ''
                    pt_net_days = pt_line.nb_days or ''
                break

            payment_items += f"""<PaymentTerms>
                        <TermsType>{'01'}</TermsType>
                        <TermsDiscountPercentage>{pt_discount_percentage}</TermsDiscountPercentage>
                        <TermsDiscountDueDays>{pt_discount_days}</TermsDiscountDueDays>
                        <TermsNetDueDays>{pt_net_days}</TermsNetDueDays>
                        <TermsDiscountAmount>{pt_discount_amount}</TermsDiscountAmount>
                        <TermsDescription>{ payment_description or ''}</TermsDescription>
                    </PaymentTerms>"""
        return payment_items


    def multistore_inv_generate_header_xml(self):
        header_xml = f"""<Header>
                <InvoiceHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <InvoiceNumber>{self.name}</InvoiceNumber>
                    <InvoiceDate>{self.invoice_date or ''}</InvoiceDate>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date() or ''}</PurchaseOrderDate>
                    <PurchaseOrderNumber>{self.edi_order_number or ''}</PurchaseOrderNumber>
                    <InvoiceTypeCode>{'DR'}</InvoiceTypeCode>
                    <TsetPurposeCode>{self.edi_tset_purpose_code or ''}</TsetPurposeCode>
                    <BuyersCurrency></BuyersCurrency>
                    <Department>{'SPS'}</Department>
                    <Vendor>{self.edi_vendor_number or ''}</Vendor>
                    <BillOfLadingNumber></BillOfLadingNumber>
                    <ShipDate></ShipDate>
                </InvoiceHeader>
                {self.multistore_inv_generate_pay_term_xml()}
                <Dates>
                    <DateTimeQualifier>{'002'}</DateTimeQualifier>
                    <Date>{self.invoice_date}</Date>
                </Dates>
                <Contacts>
                    <ContactTypeCode>IC</ContactTypeCode>
                    <ContactName>{self.partner_id.name}</ContactName>
                    <PrimaryPhone>{self.partner_id.phone or ''}</PrimaryPhone>
                    <PrimaryFax></PrimaryFax>
                    <PrimaryEmail>{self.partner_id.email}</PrimaryEmail>
                </Contacts>
                <Address>
                    <AddressTypeCode>{'BT'}</AddressTypeCode>
                    <LocationCodeQualifier>{self.edi_bt_loc_code_qualifier or ''}</LocationCodeQualifier>
                    <AddressLocationNumber>{self.edi_bt_addr_loc_number or ''}</AddressLocationNumber>
                    <AddressName>{self.partner_id.name}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.partner_id.street or ''}</Address1>
                    <Address2>{self.partner_id.street2 or ''}</Address2>
                    <City>{self.partner_id.city}</City>
                    <State>{self.partner_id.state_id.code}</State>
                    <PostalCode>{self.partner_id.zip}</PostalCode>
                    <Country>{self.partner_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>RI</AddressTypeCode>
                    <LocationCodeQualifier></LocationCodeQualifier>
                    <AddressLocationNumber></AddressLocationNumber>
                    <AddressName>{self.company_id.name or ''}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.company_id.street or ''}</Address1>
                    <Address2>{self.company_id.street2 or ''}</Address2>
                    <City>{self.company_id.city}</City>
                    <State>{self.company_id.state_id.code}</State>
                    <PostalCode>{self.company_id.zip}</PostalCode>
                    <Country>{self.company_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>{'ST'}</AddressTypeCode>
                    <LocationCodeQualifier>{self.edi_st_loc_code_qualifier or ''}</LocationCodeQualifier>
                    <AddressLocationNumber>{self.edi_st_addr_loc_number or ''}</AddressLocationNumber>
                    <AddressName>{self.partner_shipping_id.name or ''}</AddressName>
                    <Address1>{self.partner_shipping_id.street or ''}</Address1>
                    <Address2>{self.partner_shipping_id.street2 or ''}</Address2>
                    <City>{self.partner_shipping_id.city}</City>
                    <State>{self.partner_shipping_id.state_id.code}</State>
                    <PostalCode>{self.partner_shipping_id.zip}</PostalCode>
                    <Country>{self.partner_shipping_id.country_id.code}</Country>
                </Address>
                <References>
                    <ReferenceQual></ReferenceQual>
                    <ReferenceID></ReferenceID>
                    <Description></Description>
                </References>
                <Notes>
                    <NoteCode></NoteCode>
                    <Note></Note>
                </Notes>
                <FOBRelatedInstruction>
                    <FOBPayCode></FOBPayCode>
                    <FOBLocationQualifier></FOBLocationQualifier>
                    <FOBLocationDescription></FOBLocationDescription>
                </FOBRelatedInstruction>
                <CarrierInformation>
                    <StatusCode></StatusCode>
                    <CarrierTransMethodCode></CarrierTransMethodCode>
                    <CarrierAlphaCode></CarrierAlphaCode>
                    <CarrierRouting></CarrierRouting>
                    <EquipmentDescriptionCode></EquipmentDescriptionCode>
                    <CarrierEquipmentNumber></CarrierEquipmentNumber>
                    <SealNumbers>
                        <SealNumber></SealNumber>
                    </SealNumbers>
                </CarrierInformation>
                <QuantityTotals>
                    <QuantityTotalsQualifier>{'SQT'}</QuantityTotalsQualifier>
                    <Quantity></Quantity>
                    <QuantityUOM></QuantityUOM>
                </QuantityTotals>
            </Header>"""
        return header_xml

    def multistore_inv_generate_lineitem_xml(self):
        line_xml= f""""""
        sale_line_ids = self.env['sale.order.line']
        line_sequence_number = ''
        vendor_part_number = ''
        buyer_part_number = ''
        consumer_package_code = ''
        product_uom_qty = ''
        product_uom = ''
        ship_uom = ''
        ship_qty = 0

        for line in self.invoice_line_ids:
            sale_line_ids |= line.sale_line_ids
            for sale_lines in sale_line_ids:
                line_sequence_number = sale_lines.line_sequence_number
                vendor_part_number = sale_lines.edi_vendor_part_number or sale_lines.product_id.name or ''
                buyer_part_number = sale_lines.s_edi_vendor_prod_code or ''
                consumer_package_code = sale_lines.product_id.barcode or ''
                product_uom_qty = sale_lines.product_uom_qty
                product_uom = sale_lines.product_uom.edi_uom_code
                stock_move_ids = sale_lines.move_ids.filtered(
                    lambda x: x.picking_id and x.picking_id.picking_type_id
                                and x.picking_id.picking_type_id.sequence_code == 'OUT')
                for stock_id in stock_move_ids:
                    ship_qty = stock_id.quantity
                    ship_uom = stock_id.product_uom.name

            line_xml += f"""<LineItem>
                    <InvoiceLine>
                        <LineSequenceNumber>{line_sequence_number}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <InvoiceQty>{line.quantity}</InvoiceQty>
                        <InvoiceQtyUOM>{line.product_uom_id.edi_uom_code}</InvoiceQtyUOM>
                        <PurchasePrice>{line.price_unit}</PurchasePrice>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_uom}</ShipQtyUOM>
                        <ExtendedItemTotal></ExtendedItemTotal>
                    </InvoiceLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode>{'08'}</ProductCharacteristicCode>
                        <ProductDescription>{line.name or ''}</ProductDescription>
                    </ProductOrItemDescription>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </LineItem>"""
        return line_xml

    def multistore_inv_generate_summary_xml(self):
        summary_xml = f"""<Summary>
                <TotalAmount>{self.amount_total}</TotalAmount>
                <TotalSalesAmount></TotalSalesAmount>
                <TotalTermsDiscountAmount></TotalTermsDiscountAmount>
                <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
                <InvoiceAmtDueByTermsDate></InvoiceAmtDueByTermsDate>
            </Summary>"""
        return summary_xml

    def multistore_inv_generate_xml(self):
        data_xml = f""""""
        for rec in self:
            data_xml = f"""<Invoice>
                {rec.multistore_inv_generate_header_xml()}
                {rec.multistore_inv_generate_lineitem_xml()}
                {rec.multistore_inv_generate_summary_xml()}
            </Invoice>"""
        return data_xml

    #////////////////////////////////////// INV BulkImport

    def bulkimport_inv_generate_pay_term_xml(self):
        payment_items = f""""""
        for payment in self.invoice_payment_term_id:
            payment_description = payment.note
            pt_discount_percentage = 0
            pt_discount_days = 0
            pt_net_days = 0
            pt_discount_amount = ''
            pt_type = ''
            for pt_line in payment.line_ids:
                pt_type = pt_line.value
                if pt_type == 'balance':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'percent':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'fixed':
                    pt_discount_amount = pt_line.value_amount or ''
                    pt_net_days = pt_line.nb_days or ''
                break

            payment_items += f"""<PaymentTerms>
                        <TermsType>{'01'}</TermsType>
                        <TermsDiscountPercentage>{pt_discount_percentage}</TermsDiscountPercentage>
                        <TermsDiscountDueDays>{pt_discount_days}</TermsDiscountDueDays>
                        <TermsNetDueDays>{pt_net_days}</TermsNetDueDays>
                        <TermsDiscountAmount>{pt_discount_amount}</TermsDiscountAmount>
                        <TermsDescription>{ payment_description or ''}</TermsDescription>
                    </PaymentTerms>"""
        return payment_items


    def bulkimport_inv_generate_header_xml(self):
        header_xml = f"""<Header>
                <InvoiceHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <InvoiceNumber>{self.name}</InvoiceNumber>
                    <InvoiceDate>{self.invoice_date or ''}</InvoiceDate>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date() or ''}</PurchaseOrderDate>
                    <PurchaseOrderNumber>{self.edi_order_number or ''}</PurchaseOrderNumber>
                    <InvoiceTypeCode>{'DR'}</InvoiceTypeCode>
                    <TsetPurposeCode>{self.edi_tset_purpose_code or ''}</TsetPurposeCode>
                    <BuyersCurrency></BuyersCurrency>
                    <Department>{'SPS'}</Department>
                    <Vendor>{self.edi_vendor_number or ''}</Vendor>
                    <BillOfLadingNumber></BillOfLadingNumber>
                    <ShipDate></ShipDate>
                </InvoiceHeader>
                {self.bulkimport_inv_generate_pay_term_xml()}
                <Dates>
                    <DateTimeQualifier>{'002'}</DateTimeQualifier>
                    <Date>{self.invoice_date}</Date>
                    <Time></Time>
                </Dates>
                <Contacts>
                    <ContactTypeCode>IC</ContactTypeCode>
                    <ContactName>{self.partner_id.name}</ContactName>
                    <PrimaryPhone>{self.partner_id.phone or ''}</PrimaryPhone>
                    <PrimaryFax></PrimaryFax>
                    <PrimaryEmail>{self.partner_id.email}</PrimaryEmail>
                </Contacts>
                <Address>
                    <AddressTypeCode>{'BT'}</AddressTypeCode>
                    <LocationCodeQualifier>{self.edi_bt_loc_code_qualifier or ''}</LocationCodeQualifier>
                    <AddressLocationNumber>{self.edi_bt_addr_loc_number or ''}</AddressLocationNumber>
                    <AddressName>{self.partner_id.name}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.partner_id.street or ''}</Address1>
                    <Address2>{self.partner_id.street2 or ''}</Address2>
                    <City>{self.partner_id.city}</City>
                    <State>{self.partner_id.state_id.code}</State>
                    <PostalCode>{self.partner_id.zip}</PostalCode>
                    <Country>{self.partner_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>RI</AddressTypeCode>
                    <LocationCodeQualifier></LocationCodeQualifier>
                    <AddressLocationNumber></AddressLocationNumber>
                    <AddressName>{self.company_id.name or ''}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.company_id.street or ''}</Address1>
                    <Address2>{self.company_id.street2 or ''}</Address2>
                    <City>{self.company_id.city}</City>
                    <State>{self.company_id.state_id.code}</State>
                    <PostalCode>{self.company_id.zip}</PostalCode>
                    <Country>{self.company_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>{'ST'}</AddressTypeCode>
                    <LocationCodeQualifier>{self.edi_st_loc_code_qualifier or ''}</LocationCodeQualifier>
                    <AddressLocationNumber>{self.edi_st_addr_loc_number or ''}</AddressLocationNumber>
                    <AddressName>{self.partner_shipping_id.name or ''}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.partner_shipping_id.street or ''}</Address1>
                    <Address2>{self.partner_shipping_id.street2 or ''}</Address2>
                    <City>{self.partner_shipping_id.city}</City>
                    <State>{self.partner_shipping_id.state_id.code}</State>
                    <PostalCode>{self.partner_shipping_id.zip}</PostalCode>
                    <Country>{self.partner_shipping_id.country_id.code}</Country>
                </Address>
                <References>
                    <ReferenceQual></ReferenceQual>
                    <ReferenceID></ReferenceID>
                    <Description></Description>
                </References>
                <Notes>
                    <NoteCode></NoteCode>
                    <Note></Note>
                </Notes>
                <Taxes>
                    <TaxTypeCode>{'PG'}</TaxTypeCode>
                    <TaxAmount>{self.amount_tax}</TaxAmount>
                    <TaxPercent></TaxPercent>
                    <JurisdictionQual></JurisdictionQual>
                    <JurisdictionCode></JurisdictionCode>
                    <TaxExemptCode></TaxExemptCode>
                    <TaxID></TaxID>
                </Taxes>
                <ChargesAllowances>
                    <AllowChrgIndicator>{'A'}</AllowChrgIndicator>
                    <AllowChrgCode>{'C310'}</AllowChrgCode>
                    <AllowChrgAmt></AllowChrgAmt>
                    <AllowChrgPercent></AllowChrgPercent>
                    <AllowChrgHandlingCode></AllowChrgHandlingCode>
                    <AllowChrgHandlingDescription></AllowChrgHandlingDescription>
                </ChargesAllowances>
                <FOBRelatedInstruction>
                    <FOBPayCode></FOBPayCode>
                    <FOBLocationQualifier></FOBLocationQualifier>
                    <FOBLocationDescription></FOBLocationDescription>
                </FOBRelatedInstruction>
                <CarrierInformation>
                    <StatusCode></StatusCode>
                    <CarrierTransMethodCode></CarrierTransMethodCode>
                    <CarrierAlphaCode></CarrierAlphaCode>
                    <CarrierRouting></CarrierRouting>
                    <EquipmentDescriptionCode></EquipmentDescriptionCode>
                    <CarrierEquipmentNumber></CarrierEquipmentNumber>
                    <SealNumbers>
                        <SealNumber></SealNumber>
                    </SealNumbers>
                </CarrierInformation>
                <QuantityTotals>
                    <QuantityTotalsQualifier>{'SQT'}</QuantityTotalsQualifier>
                    <Quantity></Quantity>
                    <QuantityUOM></QuantityUOM>
                </QuantityTotals>
            </Header>"""
        return header_xml

    def bulkimport_inv_generate_lineitem_xml(self):
        line_xml= f""""""
        sale_line_ids = self.env['sale.order.line']
        line_sequence_number = ''
        vendor_part_number = ''
        buyer_part_number = ''
        consumer_package_code = ''
        product_uom_qty = ''
        product_uom = ''
        ship_uom = ''
        ship_qty = 0

        for line in self.invoice_line_ids:
            sale_line_ids |= line.sale_line_ids
            for sale_lines in sale_line_ids:
                line_sequence_number = sale_lines.line_sequence_number
                vendor_part_number = sale_lines.edi_vendor_part_number or sale_lines.product_id.name or ''
                buyer_part_number = sale_lines.s_edi_vendor_prod_code or ''
                consumer_package_code = sale_lines.product_id.barcode or ''
                product_uom_qty = sale_lines.product_uom_qty
                product_uom = sale_lines.product_uom.edi_uom_code
                stock_move_ids = sale_lines.move_ids.filtered(
                    lambda x: x.picking_id and x.picking_id.picking_type_id
                                and x.picking_id.picking_type_id.sequence_code == 'OUT')
                for stock_id in stock_move_ids:
                    ship_qty = stock_id.quantity
                    ship_uom = stock_id.product_uom.name

            line_xml += f"""<LineItem>
                    <InvoiceLine>
                        <LineSequenceNumber>{line_sequence_number}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <InvoiceQty>{line.quantity}</InvoiceQty>
                        <InvoiceQtyUOM>{line.product_uom_id.edi_uom_code}</InvoiceQtyUOM>
                        <PurchasePrice>{line.price_unit}</PurchasePrice>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_uom}</ShipQtyUOM>
                        <ExtendedItemTotal></ExtendedItemTotal>
                    </InvoiceLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode>{'08'}</ProductCharacteristicCode>
                        <ProductDescription>{line.name or ''}</ProductDescription>
                    </ProductOrItemDescription>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </LineItem>"""
        return line_xml

    def bulkimport_inv_generate_summary_xml(self):
        summary_xml = f"""<Summary>
                <TotalAmount>{self.amount_total}</TotalAmount>
                <TotalSalesAmount></TotalSalesAmount>
                <TotalTermsDiscountAmount></TotalTermsDiscountAmount>
                <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
                <InvoiceAmtDueByTermsDate></InvoiceAmtDueByTermsDate>
            </Summary>"""
        return summary_xml

    def bulkimport_inv_generate_xml(self):
        data_xml = f""""""
        for rec in self:
            data_xml = f"""<Invoice>
                {rec.bulkimport_inv_generate_header_xml()}
                {rec.bulkimport_inv_generate_lineitem_xml()}
                {rec.bulkimport_inv_generate_summary_xml()}
            </Invoice>"""
        return data_xml

     #////////////////////////////////////// INV Dropship

    def dropship_inv_generate_pay_term_xml(self):
        payment_items = f""""""
        for payment in self.invoice_payment_term_id:
            payment_description = payment.note
            pt_discount_percentage = 0
            pt_discount_days = 0
            pt_net_days = 0
            pt_discount_amount = ''
            pt_type = ''
            for pt_line in payment.line_ids:
                pt_type = pt_line.value
                if pt_type == 'balance':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'percent':
                    pt_discount_percentage = pt_line.value_amount
                    pt_net_days = pt_line.nb_days or ''

                elif pt_type == 'fixed':
                    pt_discount_amount = pt_line.value_amount or ''
                    pt_net_days = pt_line.nb_days or ''
                break

            payment_items += f"""<PaymentTerms>
                        <TermsType>{'01'}</TermsType>
                        <TermsDiscountPercentage>{pt_discount_percentage}</TermsDiscountPercentage>
                        <TermsDiscountDueDays>{pt_discount_days}</TermsDiscountDueDays>
                        <TermsNetDueDays>{pt_net_days}</TermsNetDueDays>
                        <TermsDiscountAmount>{pt_discount_amount}</TermsDiscountAmount>
                        <TermsDescription>{ payment_description or ''}</TermsDescription>
                    </PaymentTerms>"""
        return payment_items


    def dropship_inv_generate_header_xml(self):
        header_xml = f"""<Header>
                <InvoiceHeader>
                    <TradingPartnerId>{self.edi_trading_partner_id}</TradingPartnerId>
                    <InvoiceNumber>{self.name}</InvoiceNumber>
                    <InvoiceDate>{self.invoice_date or ''}</InvoiceDate>
                    <PurchaseOrderDate>{self.edi_order_date and self.edi_order_date.date() or ''}</PurchaseOrderDate>
                    <PurchaseOrderNumber>{self.edi_order_number or ''}</PurchaseOrderNumber>
                    <InvoiceTypeCode>{'DR'}</InvoiceTypeCode>
                    <TsetPurposeCode>{self.edi_tset_purpose_code or ''}</TsetPurposeCode>
                    <BuyersCurrency></BuyersCurrency>
                    <Department>{'SPS'}</Department>
                    <Vendor>{self.edi_vendor_number or ''}</Vendor>
                    <CustomerOrderNumber></CustomerOrderNumber>
                    <BillOfLadingNumber></BillOfLadingNumber>
                    <CarrierProNumber></CarrierProNumber>
                    <ShipDate></ShipDate>
                </InvoiceHeader>
                {self.dropship_inv_generate_pay_term_xml()}
                <Dates>
                    <DateTimeQualifier>{'002'}</DateTimeQualifier>
                    <Date>{self.invoice_date}</Date>
                </Dates>
                <Contacts>
                    <ContactTypeCode>IC</ContactTypeCode>
                    <ContactName>{self.partner_id.name}</ContactName>
                    <PrimaryPhone>{self.partner_id.phone or ''}</PrimaryPhone>
                    <PrimaryFax></PrimaryFax>
                    <PrimaryEmail>{self.partner_id.email}</PrimaryEmail>
                </Contacts>
                <Address>
                    <AddressTypeCode>{'BT'}</AddressTypeCode>
                    <LocationCodeQualifier>{self.edi_bt_loc_code_qualifier or ''}</LocationCodeQualifier>
                    <AddressLocationNumber>{self.edi_bt_addr_loc_number or ''}</AddressLocationNumber>
                    <AddressName>{self.partner_id.name}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.partner_id.street or ''}</Address1>
                    <Address2>{self.partner_id.street2 or ''}</Address2>
                    <City>{self.partner_id.city}</City>
                    <State>{self.partner_id.state_id.code}</State>
                    <PostalCode>{self.partner_id.zip}</PostalCode>
                    <Country>{self.partner_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>RI</AddressTypeCode>
                    <LocationCodeQualifier></LocationCodeQualifier>
                    <AddressLocationNumber></AddressLocationNumber>
                    <AddressName>{self.company_id.name or ''}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.company_id.street or ''}</Address1>
                    <Address2>{self.company_id.street2 or ''}</Address2>
                    <City>{self.company_id.city}</City>
                    <State>{self.company_id.state_id.code}</State>
                    <PostalCode>{self.company_id.zip}</PostalCode>
                    <Country>{self.company_id.country_id.code}</Country>
                </Address>
                <Address>
                    <AddressTypeCode>{'ST'}</AddressTypeCode>
                    <AddressName>{self.partner_shipping_id.name or ''}</AddressName>
                    <AddressAlternateName></AddressAlternateName>
                    <Address1>{self.partner_shipping_id.street or ''}</Address1>
                    <Address2>{self.partner_shipping_id.street2 or ''}</Address2>
                    <City>{self.partner_shipping_id.city}</City>
                    <State>{self.partner_shipping_id.state_id.code}</State>
                    <PostalCode>{self.partner_shipping_id.zip}</PostalCode>
                    <Country>{self.partner_shipping_id.country_id.code}</Country>
                </Address>
                <References>
                    <ReferenceQual></ReferenceQual>
                    <ReferenceID></ReferenceID>
                    <Description></Description>
                </References>
                <Notes>
                    <NoteCode></NoteCode>
                    <Note></Note>
                </Notes>
                <Taxes>
                    <TaxTypeCode>{'PG'}</TaxTypeCode>
                    <TaxAmount>{self.amount_tax}</TaxAmount>
                    <TaxPercent></TaxPercent>
                    <JurisdictionQual></JurisdictionQual>
                    <JurisdictionCode></JurisdictionCode>
                    <TaxExemptCode></TaxExemptCode>
                    <TaxID></TaxID>
                </Taxes>
                <ChargesAllowances>
                    <AllowChrgIndicator>{'A'}</AllowChrgIndicator>
                    <AllowChrgCode>{'C310'}</AllowChrgCode>
                    <AllowChrgAmt></AllowChrgAmt>
                    <AllowChrgPercent></AllowChrgPercent>
                    <AllowChrgHandlingCode></AllowChrgHandlingCode>
                    <AllowChrgHandlingDescription></AllowChrgHandlingDescription>
                </ChargesAllowances>
                <FOBRelatedInstruction>
                    <FOBPayCode></FOBPayCode>
                    <FOBLocationQualifier></FOBLocationQualifier>
                    <FOBLocationDescription></FOBLocationDescription>
                </FOBRelatedInstruction>
                <CarrierInformation>
                    <StatusCode></StatusCode>
                    <CarrierTransMethodCode></CarrierTransMethodCode>
                    <CarrierAlphaCode></CarrierAlphaCode>
                    <CarrierRouting></CarrierRouting>
                    <EquipmentDescriptionCode></EquipmentDescriptionCode>
                    <CarrierEquipmentNumber></CarrierEquipmentNumber>
                    <SealNumbers>
                        <SealNumber></SealNumber>
                    </SealNumbers>
                </CarrierInformation>
                <QuantityTotals>
                    <QuantityTotalsQualifier>{'SQT'}</QuantityTotalsQualifier>
                    <Quantity></Quantity>
                    <QuantityUOM></QuantityUOM>
                </QuantityTotals>
            </Header>"""
        return header_xml

    def dropship_inv_generate_lineitem_xml(self):
        line_xml= f""""""
        sale_line_ids = self.env['sale.order.line']
        line_sequence_number = ''
        vendor_part_number = ''
        buyer_part_number = ''
        consumer_package_code = ''
        product_uom_qty = ''
        product_uom = ''
        ship_uom = ''
        ship_qty = 0

        for line in self.invoice_line_ids:
            sale_line_ids |= line.sale_line_ids
            for sale_lines in sale_line_ids:
                line_sequence_number = sale_lines.line_sequence_number
                vendor_part_number = sale_lines.edi_vendor_part_number or sale_lines.product_id.name or ''
                buyer_part_number = sale_lines.s_edi_vendor_prod_code or ''
                consumer_package_code = sale_lines.product_id.barcode or ''
                product_uom_qty = sale_lines.product_uom_qty
                product_uom = sale_lines.product_uom.edi_uom_code
                stock_move_ids = sale_lines.move_ids.filtered(
                    lambda x: x.picking_id and x.picking_id.picking_type_id
                                and x.picking_id.picking_type_id.sequence_code == 'OUT')
                for stock_id in stock_move_ids:
                    ship_qty = stock_id.quantity
                    ship_uom = stock_id.product_uom.name

            line_xml += f"""<LineItem>
                    <InvoiceLine>
                        <LineSequenceNumber>{line_sequence_number}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <InvoiceQty>{line.quantity}</InvoiceQty>
                        <InvoiceQtyUOM>{line.product_uom_id.edi_uom_code}</InvoiceQtyUOM>
                        <PurchasePrice>{line.price_unit}</PurchasePrice>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_uom}</ShipQtyUOM>
                    </InvoiceLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode>{'08'}</ProductCharacteristicCode>
                        <ProductDescription>{line.name or ''}</ProductDescription>
                    </ProductOrItemDescription>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </LineItem>"""
        return line_xml

    def dropship_inv_generate_summary_xml(self):
        summary_xml = f"""<Summary>
                <TotalAmount>{self.amount_total}</TotalAmount>
                <TotalSalesAmount></TotalSalesAmount>
                <TotalTermsDiscountAmount></TotalTermsDiscountAmount>
                <TotalLineItemNumber>{self.edi_total_line_number or ''}</TotalLineItemNumber>
                <InvoiceAmtDueByTermsDate></InvoiceAmtDueByTermsDate>
            </Summary>"""
        return summary_xml

    def dropship_inv_generate_xml(self):
        data_xml = f""""""
        for rec in self:
            data_xml = f"""<Invoice>
                {rec.dropship_inv_generate_header_xml()}
                {rec.dropship_inv_generate_lineitem_xml()}
                {rec.dropship_inv_generate_summary_xml()}
            </Invoice>"""
        return data_xml

    def create_810_invoice_data_queue(self):
        try:
            filename = 'IN_' + \
                       str(datetime.now().strftime("%d_%m_%Y_%H_%M_%S"))
            file_path = os.path.join(
                self.partner_id.edi_outbound_file_path, '%s.xml' % filename)
            # data_xml = move.prepare_invoices_xml()

            # To prepare the files for dropship type order invoice
            # data_xml = move.crossdock_inv_generate_xml()
            # data_xml = move.multistore_inv_generate_xml()
            # data_xml = move.bulkimport_inv_generate_xml()
            data_xml = self.dropship_inv_generate_xml()
            # Create attachment and link with the Invoice
            attachment_id = self.env['ir.attachment'].create({
                'name': f'{filename}.xml',
                'res_id': self.id,
                'res_model': 'account.move',
                'datas': base64.encodebytes(bytes(data_xml, 'utf-8')),
                'mimetype': 'application/xml',
            })
            if self.edi_config_id and file_path and data_xml:
                invoice_queue_id = self.env['invoice.data.queue'].create({
                    'edi_config_id': self.edi_config_id.id,
                    'edi_order': self.edi_order_number,
                    'move_id': self.id,
                    'path': file_path,
                    'edi_order_data': data_xml,
                })
                self.update({
                    'edi_invoice_dq_id': invoice_queue_id
                })
                invoice_queue_id.export_data()
        except Exception as e:
            raise ValidationError(_(str(e)))


    def check_trading_partner_field(self, edi_order_data, trading_partner_field_ids):
        """Fetch the value from Partner SPS Field and raise a warning if the required tag value is not in XML."""
        missing_fields = set()

        for record in trading_partner_field_ids.filtered(lambda a:a.document_type=='invoice_ack'):
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

    def action_post(self):
        """
        This function is used to create a record in invoice data queue when the invoice is confirmed.
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        res = super(AccountInvoice, self).action_post()
        for move in self:
            if move.edi_config_id:
                data_xml = self.dropship_inv_generate_xml()
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

                if move.partner_id and move.partner_id.edi_810 and move.partner_id.edi_outbound_file_path:
                    move.with_delay(description="Creating 810 Invoice Date Queue Records for Invoice - %s" % move.name,  max_retries=5).create_810_invoice_data_queue()
        return res


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    s_edi_vendor_prod_code = fields.Char(
        string="EDI Vendor Product Code", store=True, compute='_compute_buyer_part_number')

    @api.depends('move_id.edi_config_id', 'product_id')
    def _compute_buyer_part_number(self):
        """
        This function is used to update the buyer product code in account move line
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        for rec in self:
            if rec.move_id and rec.move_id.edi_config_id:
                for line in rec.sale_line_ids:
                    rec.s_edi_vendor_prod_code = line.s_edi_vendor_prod_code
            else:
                rec.s_edi_vendor_prod_code = ''
