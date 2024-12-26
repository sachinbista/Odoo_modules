# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

import os
from datetime import datetime
import base64
import xml.dom.minidom
import io
import tempfile
import shutil

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _compute_856_rec_count(self):
        for pick in self:
            rec_856_count = self.env['shipment.data.queue'].search([('picking_id', '=', pick.id)])
            pick.rec_856_count = len(rec_856_count.ids)

    edi_config_id = fields.Many2one(
        'edi.config', string='EDI Config', readonly=True)
    edi_outbound_file_path = fields.Char(
        string="Outbound File path", readonly=True)
    edi_shipment_dq_id = fields.Many2one(
        'shipment.data.queue', string="Shipment Data Queue")
    edi_order_number = fields.Char(
        related='sale_id.edi_order_number', string="EDI Order Number", readonly=True)
    edi_trading_partner_id = fields.Char(related='sale_id.edi_trading_partner_id', string="Trading Partner ID",
                                         readonly=True)
    rec_856_count = fields.Integer(string='Delivery Orders', compute='_compute_856_rec_count')

    def action_view_856_records(self):
        self.ensure_one()
        rec_856_count = self.env['shipment.data.queue'].search([('picking_id', '=', self.id)])
        action = self.env["ir.actions.actions"]._for_xml_id("bista_sps_connector.edi_config_856_shipment_data")

        if len(rec_856_count) > 1:
            action['domain'] = [('id', 'in', rec_856_count.ids)]
        elif rec_856_count:
            form_view = [(self.env.ref('bista_sps_connector.edi_configuration_shipment_order_queue_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = rec_856_count.id
        return action

    # @api.model
    # def create(self, vals):
    #     """
    #     This function is to update edi_config value on creation
    #     @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
    #     :return:
    #     """
    #     res = super(StockPicking, self).create(vals)
    #     partner_id = self.env['res.partner'].browse(vals.get('partner_id'))
    #     for record in res:
    #         if 'partner_id' in vals:
    #             record.update({
    #                 'edi_config_id': partner_id.edi_config_id,
    #                 'edi_outbound_file_path': partner_id.edi_outbound_file_path
    #             })
    #     return res

    # def write(self, vals):
    #     """
    #     This function is to update edi_config value
    #     @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
    #     :return:
    #     """
    #     res = super(StockPicking, self).write(vals)
    #     if 'partner_id' in vals:
    #         partner_id = self.env['res.partner'].browse(vals.get('partner_id'))
    #         for record in self:
    #             record.update({
    #                 'edi_config_id': partner_id.edi_config_id,
    #                 'edi_outbound_file_path': partner_id.edi_outbound_file_path
    #             })
    #     return res

    def carrier_details(self, record):
        return """
                  <References>
                    <ReferenceQual></ReferenceQual>
                    <ReferenceID></ReferenceID>
                    <Description></Description>
                  </References>
                  """

    def prepare_shipment_xml(self):
        """
        This function is used to prepare xml document with shipment values
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        items = """<Shipments>
            
        """

        for picking in self:
            items += """<Shipment> 
            """
            items += """<Header> 
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
            edi_partner_id = picking.sale_id.edi_trading_partner_id
            shipment_identification = picking.name
            ship_date = picking.date_done.date()
            ship_time = picking.date_done.time()
            tset_purpose_code = picking.sale_id.edi_tset_purpose_code or ''
            ship_notice_date = picking.sale_id.date_order.date()
            ship_notice_time = picking.sale_id.date_order.time()
            currency = picking.sale_id.edi_buyers_currency or ''
            items += """
                            <ShipmentHeader>
                                <TradingPartnerId>%s</TradingPartnerId>
                                <ShipmentIdentification>%s</ShipmentIdentification>
                                <ShipDate>%s</ShipDate>
                                <ShipmentTime>%s</ShipmentTime>
                                <TsetPurposeCode>%s</TsetPurposeCode>
                                <ShipNoticeDate>%s</ShipNoticeDate>
                                <ShipNoticeTime>%s</ShipNoticeTime>
                                <ASNStructureCode>0001</ASNStructureCode>
                                <BuyersCurrency>%s</BuyersCurrency>
                            </ShipmentHeader>
                            """ % (edi_partner_id, shipment_identification,
                                   ship_date, ship_time, tset_purpose_code,
                                   ship_notice_date, ship_notice_time,
                                   currency)
            items += """
                            <Address>
                              <AddressTypeCode>SF</AddressTypeCode>
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
                        """ % (picking.company_id.name,
                               picking.company_id.street, picking.company_id.street2 or '',
                               picking.company_id.city,
                               picking.company_id.state_id.code , picking.company_id.zip,
                               picking.company_id.country_id.code)
            edi_st_addr_loc_number = picking.sale_id.edi_st_addr_loc_number or ''
            edi_st_addr_loc_qualifier = picking.sale_id.edi_st_loc_code_qualifier or ''
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
                        """ % (edi_st_addr_loc_number, edi_st_addr_loc_qualifier, picking.partner_id.name,
                               picking.partner_id.street, picking.partner_id.street2,
                               picking.partner_id.city,
                               picking.partner_id.state_id.code, picking.partner_id.zip,
                               picking.partner_id.country_id.code)
            items += self.carrier_details(picking)
            # items += """
            #             <CarrierInformation>
            #                 <CarrierTransMethodCode></CarrierTransMethodCode>
            #                 <CarrierAlphaCode></CarrierAlphaCode>
            #                 <CarrierRouting></CarrierRouting>
            #                 <EquipmentDescriptionCode></EquipmentDescriptionCode>
            #                 <CarrierEquipmentInitial></CarrierEquipmentInitial>
            #                 <CarrierEquipmentNumber></CarrierEquipmentNumber>
            #               </CarrierInformation>
            # """

            total_quantity = round(sum(picking.move_ids_without_package.mapped('quantity_done')))
            items += """
                            <QuantityAndWeight>
                                <PackingMedium>CTN</PackingMedium>
                                <PackingMaterial></PackingMaterial>
                                <LadingQuantity>%s</LadingQuantity>
                                <WeightQualifier>G</WeightQualifier>
                                <Weight>%s</Weight>
                                <WeightUOM>%s</WeightUOM>
                            </QuantityAndWeight>
                    """ % (total_quantity, picking.weight or '',
                           picking.weight_uom_name)

            items += """
            </Header>
            """
            edi_po_number = picking.sale_id.edi_order_number or ''
            edi_order_date = picking.sale_id.edi_order_date or ''
            deliver_date_done = picking.date_done
            items += """
            <OrderLevel>
                <OrderHeader>
                    <PurchaseOrderNumber>%s</PurchaseOrderNumber>
                    <PurchaseOrderDate>%s</PurchaseOrderDate>
                    <Vendor></Vendor>
                    <CustomerOrderNumber></CustomerOrderNumber>
                    <DeliveryDate>%s</DeliveryDate>
                    <DeliveryTime>%s</DeliveryTime>
                </OrderHeader>
                                """ % (edi_po_number, edi_order_date, deliver_date_done.date() or '',
                                       deliver_date_done.time() or '')
            items += """
                <PackLevel>
                    <Pack>
                      <PackLevelType>P</PackLevelType>
                      <ShippingSerialID></ShippingSerialID>
                      <CarrierPackageID></CarrierPackageID>
                    </Pack>
                    """
            items += """
                     <ItemLevel>
                    """
            count = 0
            for line in picking.move_ids_without_package:
                sale_line_record = line.sale_line_id
                buyer_part_number = sale_line_record.s_edi_vendor_prod_code
                vendor_part_number = sale_line_record.edi_vendor_part_number or sale_line_record.product_id.name or ''
                consumer_package_code = sale_line_record.product_id.barcode
                order_qty = sale_line_record.product_uom_qty
                order_qty_uom = sale_line_record.product_uom.uom_code
                material_description = sale_line_record.product_id.name
                for ml in line.move_line_ids:
                    ship_qty = ml.qty_done
                    ship_qty_uom = ml.product_uom_id.uom_code
                    product_material_code = ml.lot_id.name or ''
                    count += 1
                    items += """
                        <ShipmentLine>
                            <LineSequenceNumber>%s</LineSequenceNumber>
                            <BuyerPartNumber>%s</BuyerPartNumber>
                            <VendorPartNumber>%s</VendorPartNumber>
                            <ConsumerPackageCode>%s</ConsumerPackageCode>
                            <OrderQty>%s</OrderQty>
                            <OrderQtyUOM>%s</OrderQtyUOM>
                            <ShipQty>%s</ShipQty>
                            <ShipQtyUOM>%s</ShipQtyUOM>
                            <ShipDate>%s</ShipDate>
                            <ProductMaterialCode>%s</ProductMaterialCode>
                            <ProductMaterialDescription>%s</ProductMaterialDescription>
                        </ShipmentLine>
                                    """ % (count, buyer_part_number, consumer_package_code, vendor_part_number,
                                           order_qty, order_qty_uom, ship_qty, ship_qty_uom,
                                           picking.date_done.date(), product_material_code, material_description)

            items += """      
                    </ItemLevel>
                </PackLevel>
            </OrderLevel>
                  """
            items += """      
            <Summary>
              <TotalLineItemNumber>%s</TotalLineItemNumber>
            </Summary>
                  """ % picking.sale_id.edi_total_line_number or ''

            items += """
        </Shipment>
            """
        items += """
    </Shipments>
        """

        return items

    # ================================856 Documents

    # --------------------------------------Consolidated_Shipment

    def consolidated_shipment_header_xml(self):
        total_quantity = round(sum(self.move_ids_without_package.mapped('quantity')))
        sale_order_date = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.date() or ''
        sale_order_time = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.time() or ''
        header_xml = f"""<Header>
            <ShipmentHeader>
                <TradingPartnerId>{self.sale_id.edi_trading_partner_id}</TradingPartnerId>
                <ShipmentIdentification>{self.name}</ShipmentIdentification>
                <ShipDate>{self.date_done.date()}</ShipDate>
                <ShipmentTime>{self.date_done.time()}</ShipmentTime>
                <TsetPurposeCode>{self.sale_id.edi_tset_purpose_code or ''}</TsetPurposeCode>
                <ShipNoticeDate>{sale_order_date}</ShipNoticeDate>
                <ShipNoticeTime>{sale_order_time}</ShipNoticeTime>
                <ASNStructureCode>{'0001'}</ASNStructureCode>
                <BillOfLadingNumber></BillOfLadingNumber>
            </ShipmentHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
            </Dates>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
            <Notes>
                <NoteCode></NoteCode>
                <Note></Note>
            </Notes>
            <Contacts>
                <ContactTypeCode></ContactTypeCode>
                <ContactName></ContactName>
                <PrimaryPhone></PrimaryPhone>
                <PrimaryFax></PrimaryFax>
                <PrimaryEmail></PrimaryEmail>
            </Contacts>
            <Address>
                <AddressTypeCode>{'SF'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.company_id.name}</AddressName>
                <Address1>{self.company_id.street}</Address1>
                <Address2>{self.company_id.street2 or ''}</Address2>
                <City>{self.company_id.city}</City>
                <State>{self.company_id.state_id.code}</State>
                <PostalCode>{self.company_id.zip}</PostalCode>
                <Country>{self.company_id.country_id.code}</Country>
            </Address>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier>{self.sale_id.edi_st_addr_loc_number or ''}</LocationCodeQualifier>
                <AddressLocationNumber>{self.sale_id.edi_st_loc_code_qualifier or ''}</AddressLocationNumber>
                <AddressName>{self.partner_id.name}</AddressName>
                <Address1>{self.partner_id.street}</Address1>
                <Address2>{self.partner_id.street2}</Address2>
                <City>{self.partner_id.city}</City>
                <State>{self.partner_id.state_id.code}</State>
                <PostalCode>{self.partner_id.zip}</PostalCode>
                <Country>{self.partner_id.country_id.code}</Country>
            </Address>
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
            <QuantityAndWeight>
                <PackingMedium>{'CTN'}</PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity>{total_quantity}</LadingQuantity>
                <WeightQualifier>{'G'}</WeightQualifier>
                <Weight>{self.weight or ''}</Weight>
                <WeightUOM>{self.weight_uom_name}</WeightUOM>
            </QuantityAndWeight>
            <FOBRelatedInstruction>
                <FOBPayCode></FOBPayCode>
                <FOBLocationQualifier></FOBLocationQualifier>
                <FOBLocationDescripton></FOBLocationDescripton>
            </FOBRelatedInstruction>
            <QuantityTotals>
                <QuantityTotalsQualifier></QuantityTotalsQualifier>
                <Quantity></Quantity>
                <QuantityUOM></QuantityUOM>
            </QuantityTotals>
        </Header>"""
        return header_xml

    def consolidated_shipment_itemLevel_xml(self):
        itemlevel_stringg=f""
        for line in self.move_ids_without_package:
            sale_line_record = line.sale_line_id
            buyer_part_number = sale_line_record.s_edi_vendor_prod_code
            vendor_part_number = sale_line_record.edi_vendor_part_number or sale_line_record.product_id.name or ''
            consumer_package_code = sale_line_record.product_id.barcode
            count = 0
            for ml in line.move_line_ids:
                ship_qty = ml.quantity
                ship_qty_uom = ml.product_uom_id.edi_uom_code
                count += 1
                itemlevel_stringg += f"""<ItemLevel>
                    <ShipmentLine>
                        <LineSequenceNumber>{count}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_qty_uom}</ShipQtyUOM>
                    </ShipmentLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode></ProductCharacteristicCode>
                        <ProductDescription></ProductDescription>
                    </ProductOrItemDescription>
                    <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                    </Dates>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </ItemLevel>"""
        return itemlevel_stringg

    def consolidated_shipment_lineitem_xml(self):
        order_level = f"""<OrderLevel>
            <OrderHeader>
                <PurchaseOrderNumber>{self.sale_id.edi_order_number or ''}</PurchaseOrderNumber>
                <PurchaseOrderDate>{self.sale_id.edi_order_date or ''}</PurchaseOrderDate>
                <Department></Department>
                <Vendor></Vendor>
                <Division></Division>
            </OrderHeader>
            <QuantityAndWeight>
                <PackingMedium></PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity></LadingQuantity>
                <Weight></Weight>
                <Weight></Weight>
            </QuantityAndWeight>
            <Address>
                <AddressTypeCode></AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
            </Address>
            <PackLevel>
                <Pack>
                    <PackLevelType>{'P'}</PackLevelType>
                    <ShippingSerialID></ShippingSerialID>
                </Pack>
                {self.consolidated_shipment_itemLevel_xml()}
            </PackLevel>
        </OrderLevel>"""
        return order_level
    
    def consolidated_shipment_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalLineItemNumber>{self.sale_id.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def consolidated_shipment_generate_xml(self):
      for rec in self:
          data_xml = f"""<Shipment>
              {rec.consolidated_shipment_header_xml()}
              {rec.consolidated_shipment_lineitem_xml()}
              {rec.consolidated_shipment_summary_xml()}
       </Shipment>"""
                      
          return data_xml

    # --------------------------------------CrossDock

    def crossdock_shipment_header_xml(self):
        total_quantity = round(sum(self.move_ids_without_package.mapped('quantity')))
        sale_order_date = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.date() or ''
        sale_order_time = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.time() or ''
        header_xml = f"""<Header>
            <ShipmentHeader>
                <TradingPartnerId>{self.sale_id.edi_trading_partner_id}</TradingPartnerId>
                <ShipmentIdentification>{self.name}</ShipmentIdentification>
                <ShipDate>{self.date_done.date()}</ShipDate>
                <TsetPurposeCode>{self.sale_id.edi_tset_purpose_code or ''}</TsetPurposeCode>
                <ShipNoticeDate>{sale_order_date}</ShipNoticeDate>
                <ShipNoticeTime>{sale_order_time}</ShipNoticeTime>
                <ASNStructureCode>{'0001'}</ASNStructureCode>
                <BillOfLadingNumber></BillOfLadingNumber>
                <AppointmentNumber></AppointmentNumber>
                <CurrentScheduledDeliveryDate></CurrentScheduledDeliveryDate>
                <CurrentScheduledDeliveryTime></CurrentScheduledDeliveryTime>
            </ShipmentHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
            </Dates>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
            <Notes>
                <NoteCode></NoteCode>
                <Note></Note>
            </Notes>
            <Contacts>
                <ContactTypeCode></ContactTypeCode>
                <ContactName></ContactName>
                <PrimaryPhone></PrimaryPhone>
                <PrimaryFax></PrimaryFax>
                <PrimaryEmail></PrimaryEmail>
            </Contacts>
            <Address>
                <AddressTypeCode>{'SF'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.company_id.name}</AddressName>
                <Address1>{self.company_id.street}</Address1>
                <Address2>{self.company_id.street2 or ''}</Address2>
                <City>{self.company_id.city}</City>
                <State>{self.company_id.state_id.code}</State>
                <PostalCode>{self.company_id.zip}</PostalCode>
                <Country>{self.company_id.country_id.code}</Country>
            </Address>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier>{self.sale_id.edi_st_addr_loc_number or ''}</LocationCodeQualifier>
                <AddressLocationNumber>{self.sale_id.edi_st_loc_code_qualifier or ''}</AddressLocationNumber>
                <AddressName>{self.partner_id.name}</AddressName>
                <AddressAlternateName></AddressAlternateName>
                <Address1>{self.partner_id.street}</Address1>
                <Address2>{self.partner_id.street2}</Address2>
                <City>{self.partner_id.city}</City>
                <State>{self.partner_id.state_id.code}</State>
                <PostalCode>{self.partner_id.zip}</PostalCode>
                <Country>{self.partner_id.country_id.code}</Country>
            </Address>
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
            <QuantityAndWeight>
                <PackingMedium>{'CTN'}</PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity>{total_quantity}</LadingQuantity>
                <WeightQualifier>{'G'}</WeightQualifier>
                <Weight>{self.weight or ''}</Weight>
                <WeightUOM>{self.weight_uom_name}</WeightUOM>
            </QuantityAndWeight>
            <FOBRelatedInstruction>
                <FOBPayCode></FOBPayCode>
                <FOBLocationQualifier></FOBLocationQualifier>
                <FOBLocationDescripton></FOBLocationDescripton>
            </FOBRelatedInstruction>
            <QuantityTotals>
                <QuantityTotalsQualifier></QuantityTotalsQualifier>
                <Quantity></Quantity>
                <QuantityUOM></QuantityUOM>
            </QuantityTotals>
        </Header>"""
        return header_xml

    def crossdock_shipment_itemLevel_xml(self):
        itemlevel_stringg=f""
        for line in self.move_ids_without_package:
            sale_line_record = line.sale_line_id
            buyer_part_number = sale_line_record.s_edi_vendor_prod_code
            vendor_part_number = sale_line_record.edi_vendor_part_number or sale_line_record.product_id.name or ''
            consumer_package_code = sale_line_record.product_id.barcode
            order_qty = sale_line_record.product_uom_qty
            order_qty_uom = sale_line_record.product_uom.edi_uom_code
            count = 0
            for ml in line.move_line_ids:
                ship_qty = ml.quantity
                ship_qty_uom = ml.product_uom_id.edi_uom_code
                count += 1
                itemlevel_stringg += f"""<ItemLevel>
                    <ShipmentLine>
                        <LineSequenceNumber>{count}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <OrderQty>{order_qty}</OrderQty>
                        <OrderQtyUOM>{order_qty_uom}</OrderQtyUOM>
                        <PurchasePrice></PurchasePrice>
                        <ItemStatusCode></ItemStatusCode>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_qty_uom}</ShipQtyUOM>
                    </ShipmentLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode></ProductCharacteristicCode>
                        <ProductDescription></ProductDescription>
                    </ProductOrItemDescription>
                    <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                    </Dates>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </ItemLevel>"""
        return itemlevel_stringg

    def crossdock_shipment_lineitem_xml(self):
        order_level = f"""<OrderLevel>
            <OrderHeader>
                <PurchaseOrderNumber>{self.sale_id.edi_order_number or ''}</PurchaseOrderNumber>
                <ReleaseNumber></ReleaseNumber>
                <PurchaseOrderDate>{self.sale_id.edi_order_date or ''}</PurchaseOrderDate>
                <Department></Department>
                <Vendor></Vendor>
            </OrderHeader>
            <QuantityAndWeight>
                <PackingMedium></PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity></LadingQuantity>
                <WeightQualifier>G</WeightQualifier>
                <Weight></Weight>
                <WeightUOM></WeightUOM>
            </QuantityAndWeight>
            <Address>
                <AddressTypeCode></AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
            </Address>
            <PackLevel>
                <Pack>
                    <PackLevelType>{'P'}</PackLevelType>
                    <ShippingSerialID></ShippingSerialID>
                </Pack>
                <PhysicalDetails>
                    <PackQualifier></PackQualifier>
                    <PackValue></PackValue>
                    <PackSize></PackSize>
                    <PackUOM></PackUOM>
                    <PackingMedium></PackingMedium>
                    <PackingMaterial></PackingMaterial>
                </PhysicalDetails>
                {self.crossdock_shipment_itemLevel_xml()}
            </PackLevel>
        </OrderLevel>"""
        return order_level
    
    def crossdock_shipment_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalLineItemNumber>{self.sale_id.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def crossdock_shipment_generate_xml(self):
      for rec in self:
          data_xml = f"""<Shipment>
              {rec.crossdock_shipment_header_xml()}
              {rec.crossdock_shipment_lineitem_xml()}
              {rec.crossdock_shipment_summary_xml()}
       </Shipment>"""
                      
          return data_xml

    # -------------------------------------- Multistore

    def multistore_shipment_header_xml(self):
        total_quantity = round(sum(self.move_ids_without_package.mapped('quantity')))
        sale_order_date = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.date() or ''
        sale_order_time = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.time() or ''
        header_xml = f"""<Header>
            <ShipmentHeader>
                <TradingPartnerId>{self.sale_id.edi_trading_partner_id}</TradingPartnerId>
                <ShipmentIdentification>{self.name}</ShipmentIdentification>
                <ShipDate>{self.date_done.date()}</ShipDate>
                <TsetPurposeCode>{self.sale_id.edi_tset_purpose_code or ''}</TsetPurposeCode>
                <ShipNoticeDate>{sale_order_date}</ShipNoticeDate>
                <ShipNoticeTime>{sale_order_time}</ShipNoticeTime>
                <ASNStructureCode>{'0001'}</ASNStructureCode>
                <BillOfLadingNumber></BillOfLadingNumber>
                <AppointmentNumber></AppointmentNumber>
                <CurrentScheduledDeliveryDate></CurrentScheduledDeliveryDate>
                <CurrentScheduledDeliveryTime></CurrentScheduledDeliveryTime>
            </ShipmentHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
            </Dates>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
            <Notes>
                <NoteCode></NoteCode>
                <Note></Note>
            </Notes>
            <Contacts>
                <ContactTypeCode></ContactTypeCode>
                <ContactName></ContactName>
                <PrimaryPhone></PrimaryPhone>
                <PrimaryFax></PrimaryFax>
                <PrimaryEmail></PrimaryEmail>
            </Contacts>
            <Address>
                <AddressTypeCode>{'SF'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.company_id.name}</AddressName>
                <Address1>{self.company_id.street}</Address1>
                <Address2>{self.company_id.street2 or ''}</Address2>
                <City>{self.company_id.city}</City>
                <State>{self.company_id.state_id.code}</State>
                <PostalCode>{self.company_id.zip}</PostalCode>
                <Country>{self.company_id.country_id.code}</Country>
            </Address>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier>{self.sale_id.edi_st_addr_loc_number or ''}</LocationCodeQualifier>
                <AddressLocationNumber>{self.sale_id.edi_st_loc_code_qualifier or ''}</AddressLocationNumber>
                <AddressName>{self.partner_id.name}</AddressName>
                <Address1>{self.partner_id.street}</Address1>
                <Address2>{self.partner_id.street2}</Address2>
                <City>{self.partner_id.city}</City>
                <State>{self.partner_id.state_id.code}</State>
                <PostalCode>{self.partner_id.zip}</PostalCode>
                <Country>{self.partner_id.country_id.code}</Country>
            </Address>
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
            <QuantityAndWeight>
                <PackingMedium>{'CTN'}</PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity>{total_quantity}</LadingQuantity>
                <WeightQualifier>{'G'}</WeightQualifier>
                <Weight>{self.weight or ''}</Weight>
                <WeightUOM>{self.weight_uom_name}</WeightUOM>
            </QuantityAndWeight>
            <FOBRelatedInstruction>
                <FOBPayCode></FOBPayCode>
                <FOBLocationQualifier></FOBLocationQualifier>
                <FOBLocationDescripton></FOBLocationDescripton>
            </FOBRelatedInstruction>
            <QuantityTotals>
                <QuantityTotalsQualifier></QuantityTotalsQualifier>
                <Quantity></Quantity>
                <QuantityUOM></QuantityUOM>
            </QuantityTotals>
        </Header>"""
        return header_xml

    def multistore_shipment_itemLevel_xml(self):
        itemlevel_stringg=f""
        for line in self.move_ids_without_package:
            sale_line_record = line.sale_line_id
            buyer_part_number = sale_line_record.s_edi_vendor_prod_code
            vendor_part_number = sale_line_record.edi_vendor_part_number or sale_line_record.product_id.name or ''
            consumer_package_code = sale_line_record.product_id.barcode
            order_qty = sale_line_record.product_uom_qty
            order_qty_uom = sale_line_record.product_uom.edi_uom_code
            count = 0
            for ml in line.move_line_ids:
                ship_qty = ml.quantity
                ship_qty_uom = ml.product_uom_id.edi_uom_code
                count += 1
                itemlevel_stringg += f"""<ItemLevel>
                    <ShipmentLine>
                        <LineSequenceNumber>{count}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <OrderQty>{order_qty}</OrderQty>
                        <OrderQtyUOM>{order_qty_uom}</OrderQtyUOM>
                        <PurchasePrice></PurchasePrice>
                        <ItemStatusCode></ItemStatusCode>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_qty_uom}</ShipQtyUOM>
                    </ShipmentLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode></ProductCharacteristicCode>
                        <ProductDescription></ProductDescription>
                    </ProductOrItemDescription>
                    <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                    </Dates>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </ItemLevel>"""
        return itemlevel_stringg

    def multistore_shipment_lineitem_xml(self):
        order_level = f"""<OrderLevel>
            <OrderHeader>
                <PurchaseOrderNumber>{self.sale_id.edi_order_number or ''}</PurchaseOrderNumber>
                <ReleaseNumber></ReleaseNumber>
                <PurchaseOrderDate>{self.sale_id.edi_order_date or ''}</PurchaseOrderDate>
                <Department></Department>
                <Vendor></Vendor>
            </OrderHeader>
            <QuantityAndWeight>
                <PackingMedium></PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity></LadingQuantity>
                <WeightQualifier>G</WeightQualifier>
                <Weight></Weight>
                <WeightUOM></WeightUOM>
            </QuantityAndWeight>
            <Address>
                <AddressTypeCode></AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
            </Address>
            <PackLevel>
                <Pack>
                    <PackLevelType>{'P'}</PackLevelType>
                    <ShippingSerialID></ShippingSerialID>
                </Pack>
                <PhysicalDetails>
                    <PackQualifier></PackQualifier>
                    <PackValue></PackValue>
                    <PackSize></PackSize>
                    <PackUOM></PackUOM>
                    <PackingMedium></PackingMedium>
                    <PackingMaterial></PackingMaterial>
                </PhysicalDetails>
                {self.multistore_shipment_itemLevel_xml()}
            </PackLevel>
        </OrderLevel>"""
        return order_level
    
    def multistore_shipment_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalLineItemNumber>{self.sale_id.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def multistore_shipment_generate_xml(self):
      for rec in self:
          data_xml = f"""<Shipment>
              {rec.multistore_shipment_header_xml()}
              {rec.multistore_shipment_lineitem_xml()}
              {rec.multistore_shipment_summary_xml()}
       </Shipment>"""
                      
          return data_xml

    # -------------------------------------- BulkImport

    def bulkimport_shipment_header_xml(self):
        total_quantity = round(sum(self.move_ids_without_package.mapped('quantity')))
        sale_order_date = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.date() or ''
        sale_order_time = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.time() or ''
        header_xml = f"""<Header>
            <ShipmentHeader>
                <TradingPartnerId>{self.sale_id.edi_trading_partner_id}</TradingPartnerId>
                <ShipmentIdentification>{self.name}</ShipmentIdentification>
                <ShipDate>{self.date_done.date()}</ShipDate>
                <TsetPurposeCode>{self.sale_id.edi_tset_purpose_code or ''}</TsetPurposeCode>
                <ShipNoticeDate>{sale_order_date}</ShipNoticeDate>
                <ShipNoticeTime>{sale_order_time}</ShipNoticeTime>
                <ASNStructureCode>{'0001'}</ASNStructureCode>
                <BillOfLadingNumber></BillOfLadingNumber>
                <AppointmentNumber></AppointmentNumber>
                <CurrentScheduledDeliveryDate></CurrentScheduledDeliveryDate>
                <CurrentScheduledDeliveryTime></CurrentScheduledDeliveryTime>
            </ShipmentHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
                <Time></Time>
            </Dates>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
            <Notes>
                <NoteCode></NoteCode>
                <Note></Note>
            </Notes>
            <Contacts>
                <ContactTypeCode></ContactTypeCode>
                <ContactName></ContactName>
                <PrimaryPhone></PrimaryPhone>
                <PrimaryFax></PrimaryFax>
                <PrimaryEmail></PrimaryEmail>
            </Contacts>
            <Address>
                <AddressTypeCode>{'SF'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.company_id.name}</AddressName>
                <Address1>{self.company_id.street}</Address1>
                <Address2>{self.company_id.street2 or ''}</Address2>
                <City>{self.company_id.city}</City>
                <State>{self.company_id.state_id.code}</State>
                <PostalCode>{self.company_id.zip}</PostalCode>
                <Country>{self.company_id.country_id.code}</Country>
            </Address>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier>{self.sale_id.edi_st_addr_loc_number or ''}</LocationCodeQualifier>
                <AddressLocationNumber>{self.sale_id.edi_st_loc_code_qualifier or ''}</AddressLocationNumber>
                <AddressName>{self.partner_id.name}</AddressName>
                <Address1>{self.partner_id.street}</Address1>
                <Address2>{self.partner_id.street2}</Address2>
                <City>{self.partner_id.city}</City>
                <State>{self.partner_id.state_id.code}</State>
                <PostalCode>{self.partner_id.zip}</PostalCode>
                <Country>{self.partner_id.country_id.code}</Country>
            </Address>
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
            <QuantityAndWeight>
                <PackingMedium>{'CTN'}</PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity>{total_quantity}</LadingQuantity>
                <WeightQualifier>{'G'}</WeightQualifier>
                <Weight>{self.weight or ''}</Weight>
                <WeightUOM>{self.weight_uom_name}</WeightUOM>
            </QuantityAndWeight>
            <FOBRelatedInstruction>
                <FOBPayCode></FOBPayCode>
                <FOBLocationQualifier></FOBLocationQualifier>
                <FOBLocationDescripton></FOBLocationDescripton>
            </FOBRelatedInstruction>
            <QuantityTotals>
                <QuantityTotalsQualifier></QuantityTotalsQualifier>
                <Quantity></Quantity>
                <QuantityUOM></QuantityUOM>
            </QuantityTotals>
        </Header>"""
        return header_xml

    def bulkimport_shipment_itemLevel_xml(self):
        itemlevel_stringg=f""
        for line in self.move_ids_without_package:
            sale_line_record = line.sale_line_id
            buyer_part_number = sale_line_record.s_edi_vendor_prod_code
            vendor_part_number = sale_line_record.edi_vendor_part_number or sale_line_record.product_id.name or ''
            consumer_package_code = sale_line_record.product_id.barcode
            order_qty = sale_line_record.product_uom_qty
            order_qty_uom = sale_line_record.product_uom.edi_uom_code
            count = 0
            for ml in line.move_line_ids:
                ship_qty = ml.quantity
                ship_qty_uom = ml.product_uom_id.edi_uom_code
                count += 1
                itemlevel_stringg += f"""<ItemLevel>
                    <ShipmentLine>
                        <LineSequenceNumber>{count}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <OrderQty>{order_qty}</OrderQty>
                        <OrderQtyUOM>{order_qty_uom}</OrderQtyUOM>
                        <PurchasePrice></PurchasePrice>
                        <ItemStatusCode></ItemStatusCode>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_qty_uom}</ShipQtyUOM>
                    </ShipmentLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode></ProductCharacteristicCode>
                        <ProductDescription></ProductDescription>
                    </ProductOrItemDescription>
                    <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                    </Dates>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </ItemLevel>"""
        return itemlevel_stringg

    def bulkimport_shipment_lineitem_xml(self):
        order_level = f"""<OrderLevel>
            <OrderHeader>
                <PurchaseOrderNumber>{self.sale_id.edi_order_number or ''}</PurchaseOrderNumber>
                <ReleaseNumber></ReleaseNumber>
                <PurchaseOrderDate>{self.sale_id.edi_order_date or ''}</PurchaseOrderDate>
                <Department></Department>
                <Vendor></Vendor>
            </OrderHeader>
            <QuantityAndWeight>
                <PackingMedium></PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity></LadingQuantity>
                <WeightQualifier>G</WeightQualifier>
                <Weight></Weight>
                <WeightUOM></WeightUOM>
            </QuantityAndWeight>
            <PackLevel>
                <Pack>
                    <PackLevelType>{'P'}</PackLevelType>
                    <ShippingSerialID></ShippingSerialID>
                </Pack>
                <PhysicalDetails>
                    <PackQualifier></PackQualifier>
                    <PackValue></PackValue>
                    <PackSize></PackSize>
                    <PackUOM></PackUOM>
                    <PackingMedium></PackingMedium>
                    <PackingMaterial></PackingMaterial>
                </PhysicalDetails>
                {self.bulkimport_shipment_itemLevel_xml()}
            </PackLevel>
        </OrderLevel>"""
        return order_level
    
    def bulkimport_shipment_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalLineItemNumber>{self.sale_id.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def bulkimport_shipment_generate_xml(self):
      for rec in self:
          data_xml = f"""<Shipment>
              {rec.bulkimport_shipment_header_xml()}
              {rec.bulkimport_shipment_lineitem_xml()}
              {rec.bulkimport_shipment_summary_xml()}
       </Shipment>"""
                      
          return data_xml

    # -------------------------------------- bulkimport_tarelevel

    def bulkimport_tarelevel_shipment_header_xml(self):
        total_quantity = round(sum(self.move_ids_without_package.mapped('quantity')))
        sale_order_date = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.date() or ''
        sale_order_time = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.time() or ''
        header_xml = f"""<Header>
            <ShipmentHeader>
                <TradingPartnerId>{self.sale_id.edi_trading_partner_id}</TradingPartnerId>
                <ShipmentIdentification>{self.name}</ShipmentIdentification>
                <ShipDate>{self.date_done.date()}</ShipDate>
                <TsetPurposeCode>{self.sale_id.edi_tset_purpose_code or ''}</TsetPurposeCode>
                <ShipNoticeDate>{sale_order_date}</ShipNoticeDate>
                <ShipNoticeTime>{sale_order_time}</ShipNoticeTime>
                <ASNStructureCode>{'0001'}</ASNStructureCode>
                <BillOfLadingNumber></BillOfLadingNumber>
                <AppointmentNumber></AppointmentNumber>
                <CurrentScheduledDeliveryDate></CurrentScheduledDeliveryDate>
                <CurrentScheduledDeliveryTime></CurrentScheduledDeliveryTime>
            </ShipmentHeader>
            <Dates>
                <DateTimeQualifier></DateTimeQualifier>
                <Date></Date>
            </Dates>
            <References>
                <ReferenceQual></ReferenceQual>
                <ReferenceID></ReferenceID>
                <Description></Description>
            </References>
            <Notes>
                <NoteCode></NoteCode>
                <Note></Note>
            </Notes>
            <Contacts>
                <ContactTypeCode></ContactTypeCode>
                <ContactName></ContactName>
                <PrimaryPhone></PrimaryPhone>
                <PrimaryFax></PrimaryFax>
                <PrimaryEmail></PrimaryEmail>
            </Contacts>
            <Address>
                <AddressTypeCode>{'SF'}</AddressTypeCode>
                <LocationCodeQualifier></LocationCodeQualifier>
                <AddressLocationNumber></AddressLocationNumber>
                <AddressName>{self.company_id.name}</AddressName>
                <Address1>{self.company_id.street}</Address1>
                <Address2>{self.company_id.street2 or ''}</Address2>
                <City>{self.company_id.city}</City>
                <State>{self.company_id.state_id.code}</State>
                <PostalCode>{self.company_id.zip}</PostalCode>
                <Country>{self.company_id.country_id.code}</Country>
            </Address>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <LocationCodeQualifier>{self.sale_id.edi_st_addr_loc_number or ''}</LocationCodeQualifier>
                <AddressLocationNumber>{self.sale_id.edi_st_loc_code_qualifier or ''}</AddressLocationNumber>
                <AddressName>{self.partner_id.name}</AddressName>
                <Address1>{self.partner_id.street}</Address1>
                <Address2>{self.partner_id.street2}</Address2>
                <City>{self.partner_id.city}</City>
                <State>{self.partner_id.state_id.code}</State>
                <PostalCode>{self.partner_id.zip}</PostalCode>
                <Country>{self.partner_id.country_id.code}</Country>
            </Address>
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
            <QuantityAndWeight>
                <PackingMedium>{'CTN'}</PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity>{total_quantity}</LadingQuantity>
                <WeightQualifier>{'G'}</WeightQualifier>
                <Weight>{self.weight or ''}</Weight>
                <WeightUOM>{self.weight_uom_name}</WeightUOM>
            </QuantityAndWeight>
            <FOBRelatedInstruction>
                <FOBPayCode></FOBPayCode>
                <FOBLocationQualifier></FOBLocationQualifier>
                <FOBLocationDescripton></FOBLocationDescripton>
            </FOBRelatedInstruction>
            <QuantityTotals>
                <QuantityTotalsQualifier></QuantityTotalsQualifier>
                <Quantity></Quantity>
                <QuantityUOM></QuantityUOM>
            </QuantityTotals>
        </Header>"""
        return header_xml

    def bulkimport_tarelevel_shipment_itemLevel_xml(self):
        itemlevel_stringg=f""
        for line in self.move_ids_without_package:
            sale_line_record = line.sale_line_id
            buyer_part_number = sale_line_record.s_edi_vendor_prod_code
            vendor_part_number = sale_line_record.edi_vendor_part_number or sale_line_record.product_id.name or ''
            consumer_package_code = sale_line_record.product_id.barcode
            order_qty = sale_line_record.product_uom_qty
            order_qty_uom = sale_line_record.product_uom.edi_uom_code
            count = 0
            for ml in line.move_line_ids:
                ship_qty = ml.quantity
                ship_qty_uom = ml.product_uom_id.edi_uom_code
                count += 1
                itemlevel_stringg += f"""<ItemLevel>
                    <ShipmentLine>
                        <LineSequenceNumber>{count}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <OrderQty>{order_qty}</OrderQty>
                        <OrderQtyUOM>{order_qty_uom}</OrderQtyUOM>
                        <PurchasePrice></PurchasePrice>
                        <ItemStatusCode></ItemStatusCode>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_qty_uom}</ShipQtyUOM>
                    </ShipmentLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode></ProductCharacteristicCode>
                        <ProductDescription></ProductDescription>
                    </ProductOrItemDescription>
                    <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                    </Dates>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </ItemLevel>"""
        return itemlevel_stringg

    def bulkimport_tarelevel_shipment_lineitem_xml(self):
        order_level = f"""<OrderLevel>
            <OrderHeader>
                <PurchaseOrderNumber>{self.sale_id.edi_order_number or ''}</PurchaseOrderNumber>
                <ReleaseNumber></ReleaseNumber>
                <PurchaseOrderDate>{self.sale_id.edi_order_date or ''}</PurchaseOrderDate>
                <Department></Department>
                <Vendor></Vendor>
            </OrderHeader>
            <QuantityAndWeight>
                <PackingMedium></PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity></LadingQuantity>
                <WeightQualifier>G</WeightQualifier>
                <Weight></Weight>
                <WeightUOM></WeightUOM>
            </QuantityAndWeight>
            <PackLevel>
                <Pack>
                    <PackLevelType>{'T'}</PackLevelType>
                    <ShippingSerialID></ShippingSerialID>
                   </Pack>
                <PalletInformation>
                    <PalletTypeCode></PalletTypeCode>
                    <PalletTiers></PalletTiers>
                    <PalletBlocks></PalletBlocks>
                </PalletInformation>
                <PackLevel>
                    <Pack>
                        <PackLevelType>P</PackLevelType>
                        <ShippingSerialID>00007774760000006899</ShippingSerialID>
                    </Pack>
                    <PhysicalDetails>
                        <PackQualifier></PackQualifier>
                        <PackValue></PackValue>
                        <PackSize></PackSize>
                        <PackUOM></PackUOM>
                        <PackingMedium></PackingMedium>
                        <PackingMaterial></PackingMaterial>
                    </PhysicalDetails>
                    {self.bulkimport_tarelevel_shipment_itemLevel_xml()}
                </PackLevel>
            </PackLevel>
        </OrderLevel>"""
        return order_level
    
    def bulkimport_tarelevel_shipment_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalLineItemNumber>{self.sale_id.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def bulkimport_tarelevel_shipment_generate_xml(self):
      for rec in self:
          data_xml = f"""<Shipment>
              {rec.bulkimport_tarelevel_shipment_header_xml()}
              {rec.bulkimport_tarelevel_shipment_lineitem_xml()}
              {rec.bulkimport_tarelevel_shipment_summary_xml()}
       </Shipment>"""
                      
          return data_xml

    # --------------------------------------Dropship

    def dropship_shipment_header_xml(self):
        total_quantity = round(sum(self.move_ids_without_package.mapped('quantity')))
        sale_order_date = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.date() or ''
        sale_order_time = self.sale_id and self.sale_id.date_order and self.sale_id.date_order.time() or ''
        ship_done_date = self.date_done.date() or ''
        ship_done_time = self.date_done.time() or ''
        current_sch_delivery_date = self.scheduled_date.date() or ''
        current_sch_delivery_time = self.scheduled_date.time() or ''
        reference_qual = ''
        edi_ref_id = ''
        for record in self.sale_id:
            reference_qual = [edi_ref.edi_ref_qual for edi_ref in record.edi_reference_ids]
            edi_ref_id = [edi_ref.edi_ref_id for edi_ref in record.edi_reference_ids]
        header_xml = f"""<Header>
            <ShipmentHeader>
                <TradingPartnerId>{self.sale_id.edi_trading_partner_id}</TradingPartnerId>
                <ShipmentIdentification>{self.name}</ShipmentIdentification>
                <ShipDate>{self.date_done.date()}</ShipDate>
                <TsetPurposeCode>{self.sale_id.edi_tset_purpose_code or ''}</TsetPurposeCode>
                <ShipNoticeDate>{sale_order_date}</ShipNoticeDate>
                <ShipmentTime>{ship_done_time}</ShipmentTime>
                <ShipNoticeTime>{sale_order_time}</ShipNoticeTime>
                <ASNStructureCode>{'0001'}</ASNStructureCode>
                <StatusReasonCode>{'AS'}</StatusReasonCode>
                <BillOfLadingNumber></BillOfLadingNumber>
                <CarrierProNumber></CarrierProNumber>
                <AppointmentNumber></AppointmentNumber>
                    <CurrentScheduledDeliveryDate>{current_sch_delivery_date}</CurrentScheduledDeliveryDate>
                    <CurrentScheduledDeliveryTime>{current_sch_delivery_time}</CurrentScheduledDeliveryTime>
            </ShipmentHeader>
            <References>
                <ReferenceQual>{reference_qual}</ReferenceQual>
                <ReferenceID>{edi_ref_id}</ReferenceID>
                <Description></Description>
            </References>
            <Address>
                <AddressTypeCode>{'SF'}</AddressTypeCode>
                <LocationCodeQualifier>{'92'}</LocationCodeQualifier>
                <AddressLocationNumber>{self.sale_id.edi_st_addr_loc_number}</AddressLocationNumber>
                <AddressName>{self.company_id.name}</AddressName>
                <Address1>{self.company_id.street}</Address1>
                <Address2></Address2>
                <Address3>{self.company_id.street2 or ''}</Address3>
                <City>{self.company_id.city}</City>
                <State>{self.company_id.state_id.code}</State>
                <PostalCode>{self.company_id.zip}</PostalCode>
                <Country>{self.company_id.country_id.code}</Country>
            </Address>
            <CarrierInformation>
                <StatusCode>{'CL'}</StatusCode>
                <CarrierTransMethodCode>{self.sale_id.edi_carr_trans_meth_code}</CarrierTransMethodCode>
                <CarrierAlphaCode>{self.sale_id.edi_carrier_alpha_code}</CarrierAlphaCode>
                <CarrierRouting>{self.sale_id.edi_carrier_route}</CarrierRouting>
                 <ServiceLevelCodes>
                      <ServiceLevelCode>{self.sale_id.edi_carr_service_lvl_code}</ServiceLevelCode>
                </ServiceLevelCodes>
            </CarrierInformation>
            <QuantityAndWeight>
                <PackingMedium>{'CTN'}</PackingMedium>
                <PackingMaterial></PackingMaterial>
                <LadingQuantity>{total_quantity}</LadingQuantity>
                <WeightQualifier>{'G'}</WeightQualifier>
                <Weight>{self.weight or ''}</Weight>
                <WeightUOM>{self.weight_uom_name}</WeightUOM>
            </QuantityAndWeight>
            <ChargesAllowances>
                <AllowChrgIndicator>{self.sale_id.edi_allow_chrg_indicator}</AllowChrgIndicator>
                <AllowChrgCode>{self.sale_id.edi_allow_chrg_code}</AllowChrgCode>
                <AllowChrgAmt>{self.sale_id.edi_allow_chrg_amt}</AllowChrgAmt>
            </ChargesAllowances>
            <FOBRelatedInstruction>
                <FOBPayCode>{self.sale_id.edi_fob_paycode}</FOBPayCode>
                <FOBLocationQualifier></FOBLocationQualifier>
                <FOBLocationDescripton></FOBLocationDescripton>
            </FOBRelatedInstruction>            
            <Dates>
                <DateTimeQualifier>{'011'}</DateTimeQualifier>
                <Date>{ship_done_date}</Date>
            </Dates>      
            <Contacts>
                <ContactTypeCode></ContactTypeCode>                
            </Contacts>
            <Address>
                <AddressTypeCode>{'ST'}</AddressTypeCode>
                <AddressName>{self.partner_id.name}</AddressName>
                <Address1>{self.partner_id.street}</Address1>
                <Address2>{self.partner_id.street2}</Address2>
                <City>{self.partner_id.city}</City>
                <State>{self.partner_id.state_id.code}</State>
                <PostalCode>{self.partner_id.zip}</PostalCode>
                <Country>{self.partner_id.country_id.code}</Country>
            </Address>           
        </Header>"""
        return header_xml

    def dropship_shipment_itemLevel_xml(self):
        itemlevel_stringg=f""
        for line in self.move_ids_without_package:
            sale_line_record = line.sale_line_id
            buyer_part_number = sale_line_record.s_edi_vendor_prod_code
            vendor_part_number = sale_line_record.edi_vendor_part_number or sale_line_record.product_id.name or ''
            consumer_package_code = sale_line_record.product_id.barcode
            order_qty = sale_line_record.product_uom_qty
            order_qty_uom = sale_line_record.product_uom.edi_uom_code
            count = 0
            for ml in line.move_line_ids:
                ship_qty = ml.quantity
                ship_qty_uom = ml.product_uom_id.edi_uom_code
                count += 1
                itemlevel_stringg += f"""<ItemLevel>
                    <ShipmentLine>
                        <LineSequenceNumber>{count}</LineSequenceNumber>
                        <BuyerPartNumber>{buyer_part_number}</BuyerPartNumber>
                        <VendorPartNumber>{vendor_part_number}</VendorPartNumber>
                        <ConsumerPackageCode>{consumer_package_code}</ConsumerPackageCode>
                        <GTIN></GTIN>
                        <UPCCaseCode></UPCCaseCode>
                        <ProductID>
                            <PartNumberQual></PartNumberQual>
                            <PartNumber></PartNumber>
                        </ProductID>
                        <OrderQty>{order_qty}</OrderQty>
                        <OrderQtyUOM>{order_qty_uom}</OrderQtyUOM>
                        <PurchasePrice></PurchasePrice>
                        <ItemStatusCode></ItemStatusCode>
                        <ShipQty>{ship_qty}</ShipQty>
                        <ShipQtyUOM>{ship_qty_uom}</ShipQtyUOM>
                    </ShipmentLine>
                    <PriceInformation>
                        <PriceTypeIDCode></PriceTypeIDCode>
                        <UnitPrice></UnitPrice>
                    </PriceInformation>
                    <ProductOrItemDescription>
                        <ProductCharacteristicCode></ProductCharacteristicCode>
                        <ProductDescription></ProductDescription>
                    </ProductOrItemDescription>
                    <Dates>
                        <DateTimeQualifier></DateTimeQualifier>
                        <Date></Date>
                    </Dates>
                    <References>
                        <ReferenceQual></ReferenceQual>
                        <ReferenceID></ReferenceID>
                    </References>
                    <Notes>
                        <NoteCode></NoteCode>
                        <Note></Note>
                    </Notes>
                </ItemLevel>"""
        return itemlevel_stringg

    def dropship_shipment_lineitem_xml(self):
        current_date = datetime.now().date()
        current_time = datetime.now()
        reference_qual = []
        edi_ref_id = []
        edi_ref_description = []
        for record in self.sale_id.edi_reference_ids:
            reference_qual.extend([edi_ref.edi_ref_qual for edi_ref in record])
            edi_ref_id.extend([edi_ref.edi_ref_id for edi_ref in record])
            edi_ref_description.extend([edi_ref.edi_ref_description for edi_ref in record])
        count = 0
        for sale_line in self.move_ids_without_package.sale_line_id:
            ship_qty = sale_line.qty_delivered
            ship_qty_uom = sale_line.product_uom.edi_uom_code
            count += 1
            order_level = f"""<OrderLevel>
                <OrderHeader>
                    <InvoiceNumber></InvoiceNumber>
                    <PurchaseOrderNumber>{self.sale_id.edi_order_number or ''}</PurchaseOrderNumber>
                    <ReleaseNumber></ReleaseNumber>
                    <PurchaseOrderDate>{self.sale_id.edi_order_date or ''}</PurchaseOrderDate>
                    <Department></Department>
                    <Vendor>{self.sale_id.edi_vendor_number}</Vendor>
                    <CustomerOrderNumber></CustomerOrderNumber>
                </OrderHeader>
                <QuantityAndWeight>
                    <PackingMedium></PackingMedium>
                    <PackingMaterial></PackingMaterial>
                    <LadingQuantity></LadingQuantity>
                    <WeightQualifier>G</WeightQualifier>
                    <Weight></Weight>
                    <WeightUOM></WeightUOM>
                </QuantityAndWeight>
                <CarrierInformation>
                    <CarrierAlphaCode>{self.sale_id.edi_carrier_alpha_code}</CarrierAlphaCode>
                    <CarrierRouting>{self.sale_id.edi_carrier_route}</CarrierRouting>
                </CarrierInformation>
                <Dates>
                    <DateTimeQualifier>{'011'}</DateTimeQualifier>
                    <Date>{current_date}</Date>
                </Dates>
                <References>
                    <ReferenceQual>{reference_qual}</ReferenceQual>
                    <ReferenceID>{edi_ref_id}</ReferenceID>
                </References>
                <Address>
                   <AddressTypeCode>{'ST'}</AddressTypeCode>
                    <AddressName>{self.partner_id.name}</AddressName>
                    <Address1>{self.partner_id.street}</Address1>
                    <References>
                        <ReferenceQual>{reference_qual}</ReferenceQual>
                        <ReferenceID>{edi_ref_id}</ReferenceID>
                    </References>                
                </Address>
                <PackLevel>
                    <Pack>
                        <PackLevelType>{'P'}</PackLevelType>
                        <ShippingSerialID></ShippingSerialID>
                        <CarrierPackageID></CarrierPackageID>
                    </Pack>
                    <PhysicalDetails>
                        <PackQualifier></PackQualifier>
                        <PackValue></PackValue>
                        <Description></Description>
                        <PackSize></PackSize>
                        <PackUOM></PackUOM>
                        <PackingMedium></PackingMedium>
                        <PackingMaterial></PackingMaterial>
                    </PhysicalDetails>
                    <MarksAndNumbersCollection>
                        <MarksAndNumbersQualifier1></MarksAndNumbersQualifier1>
                        <MarksAndNumbers1></MarksAndNumbers1>
                    </MarksAndNumbersCollection>
                    <References>
                       <ReferenceQual>{reference_qual}</ReferenceQual>
                        <ReferenceID>{edi_ref_id}</ReferenceID>
                    </References>
                    <Address>
                        <AddressTypeCode>{self.sale_id.address_type_code}</AddressTypeCode>
                        <AddressName>{self.sale_id.edi_st_address_name}</AddressName>
                    </Address>
                    <ItemLevel>
                        <ShipmentLine>
                            <LineSequenceNumber>{count}</LineSequenceNumber>                       
                            <BuyerPartNumber>{sale_line.s_edi_vendor_prod_code}</BuyerPartNumber>
                            <VendorPartNumber>{sale_line.product_id.default_code}</VendorPartNumber>
                            <ConsumerPackageCode>{sale_line.product_id.barcode}</ConsumerPackageCode>
                            <ProductID>
                                <ItemStatusCode>{'AC'}</ItemStatusCode>
                                <ShipQty>{ship_qty}</ShipQty>
                                <ShipQtyUOM>{ship_qty_uom}</ShipQtyUOM>
                            </ProductID>            
                        </ShipmentLine>
                        <CarrierInformation>
                           <CarrierAlphaCode>{self.sale_id.edi_carrier_alpha_code}</CarrierAlphaCode>
                            <CarrierRouting>{self.sale_id.edi_carrier_route}</CarrierRouting>
                            <EquipmentType></EquipmentType>
                        </CarrierInformation>
                        <ProductOrItemDescription>
                            <ProductCharacteristicCode>{self.sale_id.edi_prod_char_code}</ProductCharacteristicCode>
                        </ProductOrItemDescription>
                        <MasterItemAttribute>
                            <ItemAttribute>
                                <Value></Value>
                            </ItemAttribute>
                        </MasterItemAttribute>
                        <Dates>
                            <DateTimeQualifier>{self.sale_id.edi_date_type}</DateTimeQualifier>
                            <Date>{current_date}</Date>
                            <Time>{current_time}</Time>
                        </Dates>
                        <References>
                            <ReferenceQual>{reference_qual}</ReferenceQual>
                            <ReferenceID>{edi_ref_id}</ReferenceID>
                            <Description>{edi_ref_description}</Description>
                        </References>
                        <Commodity>
                            <CommodityCodeQualifier></CommodityCodeQualifier>
                            <CommodityCode></CommodityCode>
                        </Commodity>
                        <Address>
                            <AddressTypeCode></AddressTypeCode>
                            <LocationCodeQualifier></LocationCodeQualifier>
                            <AddressLocationNumber></AddressLocationNumber>
                            <AddressName></AddressName>
                            <Address1></Address1>
                            <City></City>
                            <State></State>
                            <PostalCode></PostalCode>
                            <Country></Country>
                            <Contacts>
                                <ContactTypeCode></ContactTypeCode>
                            </Contacts>
                        </Address>
                        <Subline>
                            <SublineItemDetail>
                                <LineSequenceNumber>{count}</LineSequenceNumber>
                                <QtyPerUOM>{sale_line.product_uom.name}</QtyPerUOM>
                                <PurchasePrice>{sale_line.price_unit}</PurchasePrice>
                            </SublineItemDetail>
                        </Subline>
                    </ItemLevel>
                    <PackLevel>
                        <Pack>
                            <PackLevelType>{'P'}</PackLevelType>
                            <ShippingSerialID></ShippingSerialID>
                            <CarrierPackageID></CarrierPackageID>
                        </Pack>
                        <PhysicalDetails>
                            <PackQualifier></PackQualifier>
                            <PackValue></PackValue>
                            <Description></Description>
                        </PhysicalDetails>                
                    </PackLevel>
                </PackLevel>
            </OrderLevel>"""
            return order_level

    def dropship_shipment_summary_xml(self):
        summary_xml = f"""<Summary>
            <TotalLineItemNumber>{self.sale_id.edi_total_line_number or ''}</TotalLineItemNumber>
        </Summary>"""
        return summary_xml

    def dropship_shipment_generate_xml(self):
      for rec in self:
          data_xml = f"""<Shipment>
              {rec.dropship_shipment_header_xml()}
              {rec.dropship_shipment_lineitem_xml()}
              {rec.dropship_shipment_summary_xml()}
       </Shipment>"""
                      
          return data_xml

    def check_trading_partner_field(self, edi_order_data, trading_partner_field_ids):
        """Fetch the value from Partner SPS Field and raise a warning if the required tag value is not in XML."""
        missing_fields = set()

        for record in trading_partner_field_ids.filtered(lambda a: a.document_type == 'shipment_ack'):
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

    def button_validate(self):
        res = super().button_validate()
        if self.edi_config_id:
            data_xml = self.dropship_shipment_generate_xml()
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
        return res


    # ==========================================
    def create_856_shipment_data_queue(self):
        try:
            filename = 'SH_' + \
                       str(datetime.now().strftime("%d_%m_%Y_%H_%M_%S"))  # + '.xml'
            file_path = os.path.join(
                self.sale_id.partner_invoice_id.edi_outbound_file_path, '%s.xml' % filename)
            # data_xml = rec.prepare_shipment_xml()
            # data_xml = rec.consolidated_shipment_generate_xml()
            # data_xml = rec.crossdock_shipment_generate_xml()
            # data_xml = rec.multistore_shipment_generate_xml()
            # data_xml = rec.bulkimport_shipment_generate_xml()
            # data_xml = rec.bulkimport_tarelevel_shipment_generate_xml()
            data_xml = self.dropship_shipment_generate_xml()
            # Create attachment to link wit SaleOrder
            self.env['ir.attachment'].create({
                'name': f'{filename}.xml',
                'res_id': self.id,
                'res_model': 'stock.picking',
                'datas': base64.encodebytes(bytes(data_xml, 'utf-8')),
                'mimetype': 'application/xml',
            })
            # ===========================
            # # Download file at configured location
            # ubl_schema = tempfile.mktemp(suffix=".xml", prefix=filename)
            # with io.open(ubl_schema, 'w', encoding='utf-8') as data:
            #     data.write(data_xml)
            # data.close()

            # new_path = f"{rec.edi_outbound_file_path}{filename}{'.xml'}"
            # shutil.move(ubl_schema, new_path)

            # =========================

            if self.edi_config_id and file_path and data_xml:
                dq_id = self.env['shipment.data.queue'].sudo().create({
                    'edi_config_id': self.edi_config_id.id,
                    'picking_id': self.id,
                    'path': file_path,
                    'edi_order_data': data_xml,
                    'edi_order': self.sale_id.edi_order_number
                })
                self.update({'edi_shipment_dq_id': dq_id})
                dq_id.export_data()
        except Exception as e:
            raise ValidationError(_(e))

    def _action_done(self):
        """
        This function is used to create a record in shipment data queue once the delivery order is done.
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        res = super(StockPicking, self)._action_done()
        for rec in self.filtered(lambda s: s.sale_id.partner_invoice_id.edi_856 and s.picking_type_code == 'outgoing'):
            if rec.sale_id.partner_invoice_id.edi_outbound_file_path:
                rec.with_delay(description="Creating 856 Shipment Date Queue Records Transfer - %s" % rec.name, max_retries=5).create_856_shipment_data_queue()
        return res
