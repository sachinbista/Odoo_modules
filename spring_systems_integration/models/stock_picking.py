# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, Command, _
import json
from datetime import datetime
from base64 import b64decode
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    is_spring_picking = fields.Boolean("Is Spring Picking")
    scac_code = fields.Char(string="SCAC Code")
    carrier_code = fields.Char(string="Carrier Code")

    def button_validate(self):
        picking = super().button_validate()
        for pick in self:
            sale_id = pick.sale_id
            if pick.picking_type_code == 'outgoing' and sale_id and picking == True:
                spring_order = self.env["spring.edi.856"].search([('sale_order_id', '=', sale_id.id)])
                if spring_order:
                    pick.trigger_outgoing_transaction_spring(spring_order)
        return picking

    def get_documents_from_spring(self):
        sale_id = self.sale_id
        if not self.carrier_tracking_ref:
            raise UserError(_("Tracking number is not set. Please set Tracking number and try again"))
        if sale_id.external_origin == 'spring_system':
            spring_order = self.env["spring.edi.856"].search([('picking_id', '=', self.id)])
            if spring_order and spring_order.status != 'draft':
                return
            else:
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
        data = spring_order.edi_850_data or ''
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
            weight = self.shipping_weight or self.weight or 0.0
            if not weight:
                raise UserError(_("Weight is Not set"))
            ship_info = {
                'ship_to_location_id' : data.get('ship_to_location_id'),
                'ship_info_carrier_code': self.carrier_code, # FIXME
                'ship_info_tracking': self.carrier_tracking_ref,
                'ship_info_ship_date': str(self.date_done if self.date_done else datetime.now().strftime('%Y-%m-%d')),
                'ship_info_delivery_date': str(self.date_done) if self.date_done else '',
                'ship_info_status': "",
                'bill_of_lading': "",
                'master_bill_of_lading': "",
                'load_number': "",
                'trailer_number': "",
                'seal_number': "",
                # 'ship_pay_method': "CC", # FIXME
                'weight.value': str(weight),
                'weight.units_of_measure': str(self.weight_uom_name),
                'ship_info_additional': {'attributes': {
                    'total_weight': str(weight),
                    "ship_info_packaging_type": "BOX",
                    "ship_info_carrier_scac": self.scac_code,
                    "carrier_scac_code": self.scac_code # FIXME
                }},
                'ship_to_location': data.get('ship_to_location'),
                'ship_from_location': ship_from_location,
                'send_outgoing_transaction_after': 0 if context.get('no_trigger_outgoing_transaction') else 1,
            }
            edi_856_vals = {'ship_info': ship_info}
            if context.get('no_trigger_outgoing_transaction'):
                shipping_docs_requests = self._get_ship_docments_request_vals()
                edi_856_vals.update({'shipping_docs_requests': shipping_docs_requests})
            vendor = data.get('vendor', '')
            retailer = data.get('retailer', '')
            if vendor:
                edi_856_vals['vendor'] = vendor
            if retailer:
                edi_856_vals['retailer'] = retailer

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
                                    'name': self.name + 'shipping_label.pdf',
                                    'type': 'binary',
                                    'datas': shipping_label,
                                    'res_model': self._name,
                                    'res_id': self.id,
                                    'mimetype': 'application/x-pdf'})
                            elif res['document_type'] == 'shipping_packing_slip':
                                shipping_packing_slip = res['response_data'][0]
                                vals.update({'shipping_slip': shipping_packing_slip})
                                self.env['ir.attachment'].create({
                                    'name': self.name + 'shipping_packing_slip.pdf',
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
                    edi_856_id = edi_856_obj.search([('sale_order_id', '=', self.sale_id.id),
                                                     ('status', '=', 'document')], limit=1)
                    if edi_856_id:
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
            ship_info = edi_data.get('ship_info', {})
            ship_info.update({'send_outgoing_transaction_after': 1})
            self.send_edi_request(edi_data)