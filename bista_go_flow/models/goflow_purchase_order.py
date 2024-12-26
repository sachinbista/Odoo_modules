# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from datetime import timezone



class GoFlowPurchaseOrder(models.Model):
    _name = 'goflow.purchase.order'
    _description = 'Goflow Purchase Order Sync'

    instance_id = fields.Many2one(comodel_name='goflow.configuration', string='Instance')
    goflow_order_id = fields.Integer(string='Goflow Order ID')
    goflow_order_status = fields.Char(string='Goflow Order Status')
    order_number = fields.Char(string='Goflow Order No')

    purchase_order = fields.Many2one('purchase.order', string="Odoo Order ID")


    def get_bulk_purchase_order(self):
        go_flow_instance = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done'), ('sync_purchase_order', '=', True)])
        if go_flow_instance:
            default_filter = '?filters[status]=awaiting_receipt&sort_direction=desc&sort=date'
            if go_flow_instance.sync_purchase_order_filter:
                default_filter = go_flow_instance.sync_purchase_order_filter
            response = go_flow_instance._send_goflow_request('get', '/v1/purchasing/purchase-orders'+default_filter)
            response = response.json()
            # response = {
            #     "data": [
            #         {
            #             "id": 1002,
            #             "type": "standard",
            #             "purchase_order_number": "1006",
            #             "date": "2023-02-14T15:19:15.887Z",
            #             "status": "awaiting_receipt",
            #             "warehouse": {
            #                 "id": "6abf8dda-83c4-444d-9118-b1d3d04ba27a",
            #                 "name": "Default"
            #             },
            #             "vendor": {
            #                 "id": 1001,
            #                 "name": "Gemini Furniture"
            #             },
            #             "vendor_purchase_order": {
            #                 "purchase_order_number": '',
            #                 "is_submitted": True
            #             },
            #             "charges": [],
            #             "shipment": {
            #                 "expected_at": "0001-01-01T00:00:00Z",
            #                 "type": "small_parcel",
            #                 "carrier": '',
            #                 "shipping_method": '',
            #                 "address": {
            #                     "company": "Calder",
            #                     "street1": "6146 Honey Bluff Parkway",
            #                     "street2": '',
            #                     "city": "New York",
            #                     "state": "NY",
            #                     "zip_code": "10005",
            #                     "country_code": "us",
            #                     "email": '',
            #                     "phone": '',
            #                     "phone_extension": ''
            #                 }
            #             },
            #             "lines": [
            #                 {
            #                     "id": 1,
            #                     "product": {
            #                         "name": "Key Board",
            #                         "id": 1010,
            #                         "item_number": "key-board"
            #                     },
            #                     "vendor_item_number": "key-board",
            #                     "quantity": {
            #                         "amount": 20,
            #                         "measure": {
            #                             "amount": 1,
            #                             "abbreviation": "EA"
            #                         }
            #                     },
            #                     "price": {
            #                         "currency": {
            #                             "code": "usd",
            #                             "exchange_rate": ''
            #                         },
            #                         "amount": 8.0
            #                     },
            #                     "units_received": 0
            #                 }
            #             ],
            #             "tags": [],
            #             "notes": [],
            #             "summary": {
            #                 "subtotal": {
            #                     "currency": {
            #                         "code": "usd",
            #                         "exchange_rate": ''
            #                     },
            #                     "amount": 160.0
            #                 },
            #                 "total": {
            #                     "currency": {
            #                         "code": "usd",
            #                         "exchange_rate": ''
            #                     },
            #                     "amount": 160.0
            #                 }
            #             },
            #             "meta": {
            #                 "created": {
            #                     "at": "2023-02-14T15:19:15Z",
            #                     "by": {
            #                         "type": "user",
            #                         "user": {
            #                             "username": "demo-rooteam"
            #                         }
            #                     }
            #                 }
            #             }
            #         },
            #         {
            #             "id": 1001,
            #             "type": "standard",
            #             "purchase_order_number": "1003",
            #             "date": "2022-06-29T03:57:19.232Z",
            #             "status": "received",
            #             "warehouse": {
            #                 "id": "6abf8dda-83c4-444d-9118-b1d3d04ba27a",
            #                 "name": "Default"
            #             },
            #             "vendor": {
            #                 "id": 1001,
            #                 "name": "Gemini Furniture"
            #             },
            #             "vendor_purchase_order": {
            #                 "purchase_order_number": '',
            #                 "is_submitted": True
            #             },
            #             "charges": [],
            #             "shipment": {
            #                 "expected_at": "0001-01-01T00:00:00Z",
            #                 "type": "small_parcel",
            #                 "carrier": '',
            #                 "shipping_method": '',
            #                 "address": {
            #                     "company": "Calder",
            #                     "street1": "6146 Honey Bluff Parkway",
            #                     "street2": '',
            #                     "city": "New York",
            #                     "state": "NY",
            #                     "zip_code": "10005",
            #                     "country_code": "us",
            #                     "email": '',
            #                     "phone": '',
            #                     "phone_extension": ''
            #                 }
            #             },
            #             "lines": [
            #                 {
            #                     "id": 1,
            #                     "product": {
            #                         "name": "Key Board",
            #                         "id": 1010,
            #                         "item_number": "key-board"
            #                     },
            #                     "vendor_item_number": "key-board",
            #                     "quantity": {
            #                         "amount": 20,
            #                         "measure": {
            #                             "amount": 1,
            #                             "abbreviation": "EA"
            #                         }
            #                     },
            #                     "price": {
            #                         "currency": {
            #                             "code": "usd",
            #                             "exchange_rate": ''
            #                         },
            #                         "amount": 8.0
            #                     },
            #                     "units_received": 20
            #                 }
            #             ],
            #             "tags": [],
            #             "notes": [],
            #             "summary": {
            #                 "subtotal": {
            #                     "currency": {
            #                         "code": "usd",
            #                         "exchange_rate": ''
            #                     },
            #                     "amount": 160.0
            #                 },
            #                 "total": {
            #                     "currency": {
            #                         "code": "usd",
            #                         "exchange_rate": ''
            #                     },
            #                     "amount": 160.0
            #                 }
            #             },
            #             "meta": {
            #                 "created": {
            #                     "at": "2022-06-29T03:57:19Z",
            #                     "by": {
            #                         "type": "user",
            #                         "user": {
            #                             "username": "demo-rooteam"
            #                         }
            #                     }
            #                 }
            #             }
            #         }
            #     ],
            #     "next": ''
            # }

            if response:
                self.process_purchase_order(response,go_flow_instance)


    def process_purchase_order(self,response,go_flow_instance=None):
        if response:
            if 'data' in response:
                for purchase in response['data']:
                    already_exist = self.search([('goflow_order_id','=',purchase['id'])])
                    if not already_exist:
                        self.create_purchase_order(purchase,go_flow_instance)

    def create_purchase_order(self,purchase,go_flow_instance=None):
        order_lines = []
        for line in purchase['lines']:
            product = self.env['goflow.product'].search([('product_external_id', '=', line['product']['id'])], limit=1)
            if product:
                vals = (0, 0, {
                    'price_unit': line['price']['amount'],
                    'product_id': product.product_id.id,
                    'product_qty': line['quantity']['amount'],
                    'taxes_id': False
                })
                order_lines.append(vals)

        vendor = self.check_goflow_vendor(purchase['vendor'],go_flow_instance)
        # vendor = self.env['res.partner'].browse(8)
        if vendor:
            order_date = datetime.fromisoformat(purchase['date'][:-8])
            # order_date.strftime('%Y-%m-%d %H:%M')
            value = {
                'partner_id': vendor.partner_id.id,
                'date_order': order_date,
                'origin': purchase['purchase_order_number'],
                'order_line': order_lines
            }

            purchase_order = self.env['purchase.order'].sudo().create(value)

            create_mapping = self.sudo().create({
                'instance_id': go_flow_instance.id if go_flow_instance else False,
                'goflow_order_id': purchase['id'],
                'goflow_order_status': purchase['status'],
                'order_number': purchase['purchase_order_number'],
                'purchase_order': purchase_order.id
            })


    def check_goflow_vendor(self,vendor,go_flow_instance):
        vendor = self.env['goflow.vendor'].search(['|', ('goflow_vendor_id', '=', vendor['id']), ('name', '=', vendor['name'])],limit=1)
        if not vendor:
            vendor['supplier_rank'] = 1
            vendor = go_flow_instance.with_context({'is_contact': True}).create_partner(vendor)
        return vendor




