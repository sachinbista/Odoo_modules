# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, Command, _
import json
from base64 import b64decode
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def button_validate(self):
        picking = super().button_validate()
        for pick in self:
            sale_id = pick.sale_id
            if pick.picking_type_code == 'outgoing' and sale_id:
                spring_order = self.env["spring.edi.856"].search([('sale_order_id', '=', sale_id.id)])
                if spring_order:
                    pick.trigger_outgoing_transaction_spring(spring_order)
        return picking

    def get_documents_from_spring(self):
        sale_id = self.sale_id
        if not self.carrier_tracking_ref:
            raise UserError(_("Tracking number is not set. Please set Tracking number and try again"))
        if self.picking_type_code == 'outgoing' and sale_id:
            # spring_order = self.env["spring.edi.856"].search([('picking_id', '=', self.id)])
            # if spring_order:
            spring_order = self.env["spring.systems.sale.order"].search([('sale_order_id', '=', sale_id.id)])
            if spring_order:
                self.with_context(no_trigger_outgoing_transaction=True)._create_856_vals(spring_order)

    def _get_ship_docments_request_vals(self):
        shipping_docs_requests = {}
        shipping_docs_request = []
        shipping_label = {
            'document_type': "shipping_label",
            'action': "raw_data"
        }
        shipping_packing_slip = {
            'document_type': "shipping_packing_slip",
            'action': "raw_data"
        }
        shipping_docs_request.append(shipping_label)
        shipping_docs_request.append(shipping_packing_slip)
        shipping_docs_requests.update({'shipping_docs_request': shipping_docs_request})
        return shipping_docs_requests


    def _create_856_vals(self, spring_order):
        data = ''
        if spring_order.edi_850_data:
            data = spring_order.edi_850_data
        if data:
            context = self.env.context
            data = eval(data)
            shipments = {}
            shipment = []
            edi_856_vals = {}
            warehouse_partner = self.location_id.warehouse_id.partner_id
            ship_from_location = {'tp_location_name': warehouse_partner.name,
                                  'tp_location_address': warehouse_partner.street if warehouse_partner.street else '',
                                  'tp_location_city': warehouse_partner.city if warehouse_partner.city else '',
                                  'tp_location_postal': warehouse_partner.zip if warehouse_partner.zip else '',
                                  'tp_location_country_code': warehouse_partner.country_code if warehouse_partner.country_code else '',
                                  }

            ship_info = {
                'ship_to_location_id' : data.get('ship_to_location_id'),
                'ship_info_carrier_code': "ZJ",
                'ship_info_tracking': self.carrier_tracking_ref,
                'ship_info_ship_date': str(self.date_done),
                'ship_info_delivery_date': str(self.date_done),
                'ship_info_status': "",
                'bill_of_lading': "",
                'master_bill_of_lading': "",
                'load_number': "",
                'trailer_number': "",
                'seal_number': "",
                'ship_pay_method': "CC",
                'weight.value': str(self.shipping_weight),
                'weight.units_of_measure': str(self.weight_uom_name),
                'ship_info_additional': {'attributes': {
                    'total_weight': str(self.shipping_weight),
                    "ship_info_carrier_scac": "CENQ",
                    "carrier_scac_code": "CENQ"
                }},
                'ship_to_location': data.get('ship_to_location'),
                'ship_from_location': ship_from_location,
            }
            if context.get('no_trigger_outgoing_transaction'):
                ship_info.update({'send_outgoing_transaction_after': 0})
            else:
                ship_info.update({'send_outgoing_transaction_after': 1})
            edi_856_vals.update({'ship_info': ship_info})
            if context.get('no_trigger_outgoing_transaction'):
                shipping_docs_requests = self._get_ship_docments_request_vals()
                edi_856_vals.update({'shipping_docs_requests': shipping_docs_requests})
            vendor = data.get('vendor', '')
            if vendor:
                edi_856_vals.update({'vendor': vendor})

            retailer = data.get('retailer', '')
            if retailer:
                edi_856_vals.update({'retailer': retailer})

            po = []
            po_data = {
                'po_id': data.get('po_id', ''),
                'vendor_id': data.get('vendor_id', ''),
                'retailer_id': data.get('retailer_id', ''),
                'mark_for_location_id': data.get('mark_for_location_id', ''),
                'ship_to_location_id': data.get('ship_to_location_id', ''),
                'po_num': data.get('po_num', ''),
                'po_acknowledge_status': 1,
                'po_additional': data.get('po_additional', ''),
                'mark_for_location': data.get('mark_for_location', ''),

            }

            ship_carton = []
            ship_carton_data = {
                'vendor_id': data.get('vendor_id', ''),
                'po_id': data.get('po_id', ''),
            }

            po_items = data['po_items']['po_item']
            po_item_pack = []
            for line in self.move_line_ids:
                product_code = line.product_id.default_code
                item_line = list(filter(lambda item: item['product']['product_vendor_item_num'] == product_code, po_items))[0]
                po_item_pack_data = {
                    'po_item_id': item_line['po_item_id'],
                    'po_item_pack_qty': line.reserved_uom_qty,
                    'po_item': item_line,
                }
                po_item_pack.append(po_item_pack_data)

            ship_carton_data.update({'po_item_pack': po_item_pack})
            ship_carton.append(ship_carton_data)
            po_data.update({'ship_carton':ship_carton})
            po.append(po_data)
            edi_856_vals.update({'po': po})
            shipment.append(edi_856_vals)
            shipments.update({'shipment': shipment})
            end_vals = {'shipments': shipments}
            self.send_edi_request(end_vals)



    def send_edi_request(self, end_vals):
        config_id = self.env['spring.systems.configuration'].search([])
        edi_856_obj = self.env['spring.edi.856']
        for config in config_id:
            connection_url = (config.url + 'ship-incoming/send/api_user/' +
                              config.api_user + '/api_key/' + config.api_key)
            response = config._send_spring_request('post', connection_url, payload=end_vals)
            if response and response.status_code == 200:
                response_data = json.loads(response.text)
                if self.env.context.get('no_trigger_outgoing_transaction'):
                    shipments = response_data['shipments']['shipment']
                    for ship in shipments:
                        vals = {}
                        ship_id = ship['ship_info']['ship_info_id']
                        edi_856_id = edi_856_obj.search([('sale_order_id', '=', self.sale_id.id)])
                        vals.update({'spring_system_ship_id': ship_id,
                                     'edi_856_data': str(ship),
                                     'status': 'document',
                                     'picking_id': self.id,
                                     'move_ids': [Command.set(self.move_line_ids.ids)],
                                     'sale_order_id': self.sale_id.id,
                                     'vendor_id': self.partner_id.id,
                                     'notes': response_data['warnings'][0]})
                        doc_response = ship['shipping_docs_responses']['shipping_docs_response']
                        for res in doc_response:
                            if res['document_type'] == 'shipping_label':
                                shipping_label = res['response_data'][0]
                                vals.update({'shipping_label': shipping_label})
                                self.env['ir.attachment'].create({
                                    'name': self.name + 'shipping_label',
                                    'type': 'binary',
                                    'datas': shipping_label,
                                    'res_model': self._name,
                                    'res_id': self.id,
                                    'mimetype': 'application/x-pdf'})
                            elif res['document_type'] == 'shipping_packing_slip':
                                shipping_packing_slip = res['response_data'][0]
                                vals.update({'shipping_slip': shipping_packing_slip})
                                self.env['ir.attachment'].create({
                                    'name': self.name + 'shipping_packing_slip',
                                    'type': 'binary',
                                    'datas': shipping_packing_slip,
                                    'res_model': self._name,
                                    'res_id': self.id,
                                    'mimetype': 'application/x-pdf'})
                        if edi_856_id and vals:
                            edi_856_id.write(vals)
                        elif vals and not edi_856_id:
                            edi_856_obj.create(vals)
                else:
                    edi_856_id = edi_856_obj.search([('picking_id', '=', self.id)])
                    edi_856_id.write({'status': 'sent'})
            else:
                edi_856_obj.create({
                    'edi_856_data': str(end_vals),
                    'status': 'draft',
                    'picking_id': self.id,
                    'sale_order_id': self.sale_id.id,
                    'move_ids': [Command.set(self.move_line_ids.ids)],
                    'system_errors': 'ERROR'
                })



    def trigger_outgoing_transaction_spring(self, spring_order):
        data = spring_order.edi_856_data
        edi_data = {}
        if data:
            edi_data = eval(data)
        if edi_data:
            ship_info = edi_data.get('ship_info', False)
            ship_info.update({'send_outgoing_transaction_after': 1})
            self.send_edi_request(edi_data)

    def new(self):
        new = {'warnings': ['Tracking number: 256161632 has been used already for a previous shipment', 'Ship Info: 1032001 - Please only use letters and numbers, 50 characters max. Bill of Lading (BOL) numbers should be 17 digits long. Are you sure you want to proceed?'], 'shipments': {'shipment': [{'vendor': {'tp_id': 1587, 'tp_name': 'Flybar Inc', 'tp_type': 'V', 'tp_isa_id': '2127361413', 'tp_isa_qual': '12', 'tp_active': 1, 'tp_created': '2023-06-23 12:54:33', 'tp_updated': '2023-06-23 12:54:33', 'tp_additional': {'attributes': {'email': '', 'is_d2c': '', 'legacy': {'company_id': 'flybar'}, 'iso_9000': {'value': '', 'expires': ''}, 'fax_number': '', 'quickbooks': {'customer_ref': {'value': ''}}, 'phone_number': '', 'vendor_is_ppo': '', 'employer_liability_ins': {'value': '', 'expires': ''}, 'consolidation_center_code': '', 'ppo_email_distribution_list': ''}}}, 'retailer': {'tp_id': 162, 'tp_name': 'Tractor Supply', 'tp_type': 'R', 'tp_isa_id': '6120930014', 'tp_isa_qual': '08', 'tp_active': 1, 'tp_created': '2017-12-08 10:45:30', 'tp_updated': '2019-12-03 13:25:22', 'tp_additional': {'attributes': {'legacy': {'company_id': 'tractorsupply'}, 'iso_9000': {'value': '', 'expires': ''}, 'fax_number': '', 'phone_number': '', 'employer_liability_ins': {'value': '', 'expires': ''}}}}, 'transaction': {'transaction_additional': {'attributes': {'transaction_sequence_number': 1}}}, 'ship_info': {'total_cartons': 1, 'total_po_item_pack_items': 5, 'ship_info_id': 1032001, 'vendor_id': 1587, 'retailer_id': 162, 'ship_from_location_id': 4447460143, 'ship_to_location_id': 4447446286, 'ship_info_carrier_code': 'ZJ', 'ship_info_tracking': '256161632', 'ship_info_ship_date': '1969-12-31 19:00:00', 'ship_info_delivery_date': '1969-12-31 19:00:00', 'ship_info_status': 1, 'ship_info_invoice_status': 0, 'ship_info_routing_request_status': 0, 'ship_info_pickup_request_status': 0, 'ship_info_instruction_detail_status': 0, 'ship_info_created': '2023-12-08 05:44:07', 'ship_info_updated': '2023-12-08 05:44:09', 'shipment_packed_sum': 5, 'ship_info_additional': {'attributes': {'volume': {'unit_of_measure': 'CF'}, 'weight': {'value': '50.0', 'unit_of_measure': 'LB'}, 'dimensions': {'unit_of_measure': 'in'}, 'total_weight': '50.0', 'carrier_scac_code': 'CENQ', 'ship_info_carrier_scac': 'CENQ', 'packing_in_progress_flag': '0'}}, 'ship_to_location': {'tp_location_id': 4447446286, 'tp_id': 162, 'tp_location_code': '0398', 'tp_location_name': 'TSC', 'tp_location_address': '6234 BAGBY AVE', 'tp_location_city': 'WACO', 'tp_location_state_province': 'TX', 'tp_location_postal': '76712', 'tp_location_status': 1, 'tp_location_default': 0, 'tp_location_created': '2023-07-05 14:58:04', 'tp_location_updated': '2023-07-05 14:58:04', 'tp_location_additional': {'attributes': []}}, 'ship_from_location': {'tp_location_id': 4447460143, 'tp_id': 1587, 'tp_location_name': 'Flybar', 'tp_location_address': '795 W Alexander Rd', 'tp_location_city': 'Greenwood', 'tp_location_country_code': 'US', 'tp_location_status': 1, 'tp_location_default': 0, 'tp_location_created': '2023-11-28 08:04:45', 'tp_location_updated': '2023-11-28 08:04:45', 'tp_location_additional': {'attributes': []}}, 'carton_summary': [{'sequence_number': 1}]}, 'po': [{'vendor_id': 1587, 'retailer_id': 162, 'mark_for_location_id': 4447446286, 'ship_to_location_id': 4447446286, 'po_num': '4080535510', 'po_original_num': '4080535510', 'po_type': 'SA', 'po_acknowledge_status': 0, 'po_ship_request_status': 0, 'po_ship_status': 1, 'po_invoice_status': 1, 'po_ship_open_date': '2023-07-21', 'po_ship_close_date': '2023-07-24', 'po_last_asn_date': '2023-12-08 05:44:09', 'po_last_invoice_date': '2023-12-07 10:53:58', 'po_created': '2023-07-05 14:58:04', 'po_updated': '2023-12-08 05:44:09', 'po_id': 281309, 'po_additional': {'attributes': {'vendor': {'tp_isa_id': '2127361413', 'tp_isa_qual': '12', 'vendor_number': '542154'}, 'bill_to': {'tp_id': 162, 'tp_location_id': 4447446286, 'tp_location_city': 'WACO', 'tp_location_code': '0398', 'tp_location_name': 'TSC', 'tp_location_postal': '76712', 'tp_location_status': 1, 'tp_location_address': '6234 BAGBY AVE', 'tp_location_created': '2023-07-05 14:58:04', 'tp_location_default': 0, 'tp_location_updated': '2023-07-05 14:58:04', 'tp_location_additional': {'attributes': []}, 'tp_location_state_province': 'TX'}, 'retailer': {'tp_isa_id': '6120930015', 'tp_isa_qual': '08'}, 'ship_info': {'ship_info_additional': {'attributes': {'ship_info_shipping_pay_method': []}}, 'ship_info_carrier_code': []}, 'total_cost': '890', 'order_message': 'Back Order is Not Authorized', 'payment_terms': {'payment_term': {'payment_days': '60', 'payment_net_days': '60', 'payment_description': 'Net 60', 'payment_discount_days': [], 'payment_term_type_code': '05', 'payment_days_basis_code': [], 'payment_days_basis_description': []}}, 'edi_po_created': '2023-06-30 15:00', 'control_numbers': {'interchange_control_num': '000000011', 'transaction_control_num': '0001'}, 'ship_no_later_date': ['2023-07-24', '2023-07-24'], 'shipping_pay_method': 'CC', 'updated_by_860_flag': '1', 'ship_not_before_date': '2023-07-21', 'total_number_of_line_items': '1'}}, 'po_ship': {'mark_for_location_id': 4447446286, 'po_ship_key': '10320012813096572f3776aaa0', 'po_id': 281309, 'ship_info_id': 1032001, 'po_ship_created': '2023-12-08 05:44:07', 'po_ship_updated': '2023-12-08 05:44:07', 'po_ship_additional': {'attributes': []}, 'mark_for_location': {'tp_location_id': 4447446286, 'tp_id': 162, 'tp_location_code': '0398', 'tp_location_name': 'TSC', 'tp_location_address': '6234 BAGBY AVE', 'tp_location_city': 'WACO', 'tp_location_state_province': 'TX', 'tp_location_postal': '76712', 'tp_location_status': 1, 'tp_location_default': 0, 'tp_location_created': '2023-07-05 14:58:04', 'tp_location_updated': '2023-07-05 14:58:04', 'tp_location_additional': {'attributes': []}}}, 'total_cartons': 1, 'total_po_item_pack_items': 5, 'ship_carton': [{'ship_carton_key': '103200115876572f37773238', 'vendor_id': 1587, 'ship_carton_number': 411605000000052, 'ship_info_id': 1032001, 'po_id': 281309, 'ship_carton_created': '2023-12-08 05:44:07', 'ship_carton_updated': '2023-12-08 05:44:08', 'sequence_number': 0, 'ship_carton_additional': {'attributes': {'volume': {'value': '', 'unit_of_measure': 'CF'}, 'weight': {'value': '', 'unit_of_measure': 'LB'}, 'dimensions': {'width': {'value': ''}, 'height': {'value': ''}, 'length': {'value': ''}, 'unit_of_measure': 'in'}, 'ship_carton_number_details': {'check_digit': 2, 'carton_number_with_check_digit': 4116050000000522}, 'original_ship_carton_number': 411605000000052}}, 'po_item_pack': [{'po_item_pack_key': '103200118539646572f3777d2485.65693505', 'po_item_id': 1853964, 'ship_carton_key': '103200115876572f37773238', 'po_item_pack_qty': 2, 'po_item_pack_created': '2023-12-08 05:44:07', 'po_item_pack_updated': '2023-12-08 05:44:07', 'po_item_pack_additional': {'attributes': {'volume': {'value': '', 'unit_of_measure': 'CF'}, 'weight': {'value': '', 'unit_of_measure': 'LB'}, 'dimensions': {'width': {'value': ''}, 'height': {'value': ''}, 'length': {'value': ''}, 'unit_of_measure': 'in'}}}, 'po_item': {'po_item_id': 1853964, 'po_id': 281309, 'product_id': 1257124566, 'po_item_line_num': '10', 'po_item_qty_ordered': 5, 'po_item_qty_confirmed': 5, 'po_item_unit_price': 178, 'po_item_unit_price_confirmed': 178, 'po_item_uom': 'EA', 'po_item_buyer_item_num': '1868837', 'po_item_status': 'accept', 'po_item_created': '2023-07-05 14:58:04', 'po_item_updated': '2023-07-05 14:58:54', 'po_item_additional': {'attributes': {'product': {'product_additional': {'attributes': {'description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED'}, 'identifiers': {'gtin': '038675274099', 'vendor_item_num': 'KT1639TSC'}}}, 'count_item': '0', 'sum_item_qty': '0', 'product_group': {'product_group_description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED'}}}, 'shipped_items': None, 'display_values': {'gtin': '038675274099', 'vendor_item_num': 'KT1639TSC', 'size': None, 'color': None, 'group_by_code': None, 'group_by_pack': None, 'po_item_buyer_item_num': '1868837', 'weight': {'value': None, 'unit_of_measure': None}, 'dimensions': {'length': {'value': None}, 'width': {'value': None}, 'height': {'value': None}}, 'volume': {'unit_of_measure': None, 'value': None}}, 'product': {'product_id': 1257124566, 'vendor_id': 1587, 'product_code': '038675274099', 'product_code_type': 'gtin', 'product_gtin': '038675274099', 'product_vendor_item_num': 'KT1639TSC', 'product_group_id': 98823, 'product_uom': 'EA', 'product_active': 1, 'product_created': '2023-07-05 12:26:59', 'product_updated': '2023-07-05 12:26:59', 'product_additional': {'attributes': {'description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED'}, 'identifiers': {'gtin': '038675274099', 'vendor_item_num': 'KT1639TSC'}}}, 'product_group': {'product_group_description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED', 'vendor_id': 1587, 'product_group_id': 98823, 'product_group_additional': {'attributes': []}}, 'product_pack': []}}, {'po_item_pack_key': '103200118539646572f377833360.88328313', 'po_item_id': 1853964, 'ship_carton_key': '103200115876572f37773238', 'po_item_pack_qty': 3, 'po_item_pack_created': '2023-12-08 05:44:07', 'po_item_pack_updated': '2023-12-08 05:44:07', 'po_item_pack_additional': {'attributes': {'volume': {'value': '', 'unit_of_measure': 'CF'}, 'weight': {'value': '', 'unit_of_measure': 'LB'}, 'dimensions': {'width': {'value': ''}, 'height': {'value': ''}, 'length': {'value': ''}, 'unit_of_measure': 'in'}}}, 'po_item': {'po_item_id': 1853964, 'po_id': 281309, 'product_id': 1257124566, 'po_item_line_num': '10', 'po_item_qty_ordered': 5, 'po_item_qty_confirmed': 5, 'po_item_unit_price': 178, 'po_item_unit_price_confirmed': 178, 'po_item_uom': 'EA', 'po_item_buyer_item_num': '1868837', 'po_item_status': 'accept', 'po_item_created': '2023-07-05 14:58:04', 'po_item_updated': '2023-07-05 14:58:54', 'po_item_additional': {'attributes': {'product': {'product_additional': {'attributes': {'description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED'}, 'identifiers': {'gtin': '038675274099', 'vendor_item_num': 'KT1639TSC'}}}, 'count_item': '0', 'sum_item_qty': '0', 'product_group': {'product_group_description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED'}}}, 'shipped_items': None, 'display_values': {'gtin': '038675274099', 'vendor_item_num': 'KT1639TSC', 'size': None, 'color': None, 'group_by_code': None, 'group_by_pack': None, 'po_item_buyer_item_num': '1868837', 'weight': {'value': None, 'unit_of_measure': None}, 'dimensions': {'length': {'value': None}, 'width': {'value': None}, 'height': {'value': None}}, 'volume': {'unit_of_measure': None, 'value': None}}, 'product': {'product_id': 1257124566, 'vendor_id': 1587, 'product_code': '038675274099', 'product_code_type': 'gtin', 'product_gtin': '038675274099', 'product_vendor_item_num': 'KT1639TSC', 'product_group_id': 98823, 'product_uom': 'EA', 'product_active': 1, 'product_created': '2023-07-05 12:26:59', 'product_updated': '2023-07-05 12:26:59', 'product_additional': {'attributes': {'description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED'}, 'identifiers': {'gtin': '038675274099', 'vendor_item_num': 'KT1639TSC'}}}, 'product_group': {'product_group_description': '12V TRACTOR SUPPLY ZERO TURN MOWER RED', 'vendor_id': 1587, 'product_group_id': 98823, 'product_group_additional': {'attributes': []}}, 'product_pack': []}}]}]}]}]}, 'messages': ['Warehouse Shipping Advice(s) were successfully saved'], 'transaction': {'transaction_key': '9456572f37754b62', 'transaction_created': '2023-12-08 05:44:10', 'transaction_additional': {'attributes': []}}}
