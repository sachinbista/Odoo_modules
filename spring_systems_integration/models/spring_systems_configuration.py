# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import requests
import json
from .connection import SpringSystemConnection

class SpringSystemsConfiguration(models.Model):
    _name = 'spring.systems.configuration'
    _description = 'Spring Systems Configuration'

    name = fields.Char(string='Instance Name')
    url = fields.Char(string='URL')
    system_environment = fields.Selection(
        string="Environment",
        selection=[
            ('sandbox', 'Sandbox'),
            ('production', 'Production'),
        ],
        required=True,
        default='sandbox')
    api_user = fields.Char(string='API User')
    api_key = fields.Char(string='API Key')
    access_token = fields.Char(string='Spring Systems Access Token')
    company_id = fields.Many2one('res.company', string='Company')
    user_id = fields.Many2one('res.users', string='User to send Notification')

    get_po_850 = fields.Boolean(string="Get Purchase Order from Spring")
    # get_po_850_url = fields.Char(string='Get 850 URL')

    send_po_ack_855 = fields.Boolean(string="Send PO Acknowledgement to Spring")
    # send_po_ack_855_url = fields.Char(string="Send PO Acknowledgement to Spring URL")

    send_po_ack_856 = fields.Boolean(string="Send Shipment to Spring")
    # send_po_ack_856_url = fields.Char(string="Send Shipment to Spring URL")
    # api_connection = fields.Char('connection url')
    # get_product_catalog= fields.Boolean(string="Get Product Catalog")
    # get_product_catalog_url = fields.Char(string="Get Product Catalog URL")

    def _add_spring_log(self, method, query_url, response, exception):
        if method.lower() == 'patch':
            message = response.reason
        elif not exception:
            message = response.json()
        else:
            message = response

        self.env['spring.systems.error.log'].sudo().create(
            {'name': 'spring_request_log',
             'message': message,
             'api_url': query_url,
             'request': json.dumps(query_url, default=str),
             'request_type': method,
             'response': response if not exception else False,
             'status': response.status_code if not exception else False})

    def _send_spring_request(self, method, query_url, payload=False):
        headers = ''
        response = ''
        try:
            response = requests.request(method, query_url, json=payload, headers=headers)
            self._add_spring_log(method, query_url, response, exception=False)
        except Exception as e:
            self._add_spring_log(method, query_url, str(e), exception=True)
        return response

    def test_connection(self):
        env_url = self.url
        end_point = 'po-outgoing/export/'
        end_point_url = env_url + end_point
        config_id = self
        filter = '/po.filter.gt.po_created/2017-09-01T00:00:00Z'
        connection_url = end_point_url + 'api_user/' + self.api_user + '/api_key/' + self.api_key + filter
        connection_obj = SpringSystemConnection.establish_connection(connection_url, config_id)
        if connection_obj:
            message = _("Connection Test Successful!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            message = _("Connection Test Unsuccessful! Please Try Again")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'danger',
                    'sticky': False,
                }
            }


    def _auto_download_po_so_data(self):
        spring_systems_configuration_ids = self.env['spring.systems.configuration'].search([])
        for config in spring_systems_configuration_ids:
            if config.get_po_850:
                config._download_po_so_data()

    def _download_po_so_data(self):
        po_ids = False
        end_point_url = self.url + 'po-outgoing/export/'
        po_filter = '/po.filter.gt.po_created/2017-09-01'
        connection_url = end_point_url + 'api_user/' + self.api_user + '/api_key/' + self.api_key + po_filter
        so_connection_obj = {}
        so_response = self._send_spring_request('get', connection_url, payload=False)
        if so_response and so_response.status_code == 200:
            so_connection_obj = json.loads(so_response.text)
        # so_connection_obj = SpringSystemConnection.establish_connection(connection_url, config_id)
        connected_po = so_connection_obj.get('pos', {})
        if connected_po:
            po_ids = connected_po.get('po', {})
        spring_systems_so_obj = self.env['spring.systems.sale.order']
        for each in po_ids:
            vals = {}
            error = ''
            retailer = each.get('retailer', False)
            ship_to_location = each.get('ship_to_location', False)
            external_so_id = each.get('po_id', False)
            if ship_to_location:
                domain = []
                location_id = ship_to_location.get('tp_location_id', False)
                # if location_id:
                #     domain.append(('currency_id', '=', location_id))
                location_name = ship_to_location.get('tp_location_name', False)
                if location_name:
                    domain.append(('name', '=', location_name))
                tp_location_postal = ship_to_location.get('tp_location_postal', False)
                if tp_location_postal:
                    domain.append(('zip', '=', tp_location_postal))
                ship_to_location_id = self.env['res.partner'].search(domain, limit=1)
                if ship_to_location_id:
                    vals.update({'partner_shipping_id': ship_to_location_id.id})
                else:
                    error += 'Shipping Address not found for - ' + location_name

            if retailer:
                retailer_name = retailer.get('tp_name', False)
                partner_id = self.env['res.partner'].search([('name', '=', retailer_name)], limit=1)
                if partner_id:
                    vals.update({'partner_id': partner_id.id})
                else:
                    error += '\nCustomer not found for - ' + retailer_name

            additional_info = each.get('po_additional', False)
            if additional_info:
                attributes = additional_info.get('attributes', False)
                if attributes:
                    bill_to = attributes.get('bill_to', False)
                    if bill_to:
                        domain = []
                        tp_location_name = bill_to.get('tp_location_name', False)
                        if tp_location_name:
                            domain.append(('name', '=', tp_location_name))
                        tp_location_postal = bill_to.get('tp_location_postal', False)
                        if tp_location_postal:
                            domain.append(('zip', '=', tp_location_postal))
                        bill_to_location_id = self.env['res.partner'].search(domain)
                        if bill_to_location_id:
                            vals.update({'partner_invoice_id': bill_to_location_id.id})
                        else:
                            error += '\nInvoice address not found for - '+ tp_location_name
                    expiration_date = attributes.get('ship_no_later_date', False)
                    order_msg = attributes.get('order_message', False)
                    if order_msg:
                        vals.update({'note': str(order_msg)})
                    # if expiration_date:
                    #     vals.update({'validity_date': expiration_date})
                    shipping_pay_method = attributes.get('shipping_pay_method', False)
                    payment_terms = attributes.get('payment_terms', False)
                    if payment_terms:
                        payment_term = payment_terms.get('payment_term', False)
                        payment_description = payment_term.get('payment_description', False)
                        payment_days = payment_term.get('payment_days', '')
                        payment_term_line_id = self.env['account.payment.term.line'].search(
                            [('days', '=', payment_days), ('value', '=', 'balance')], limit=1)
                        if payment_term_line_id:
                            payment_term_id = payment_term_line_id.payment_id
                            vals.update({'payment_term_id': payment_term_id.id})
                        else:
                            error += '\nPayment Term not found for - ' + payment_description

            item = each.get('po_items', False)
            line_vals = []
            if item:
                po_items = item.get('po_item', False)
                for line in po_items:
                    product = line.get('product')
                    product_code = product['product_vendor_item_num']
                    product_id = self.env['product.product'].search([('default_code', '=', product_code)], limit=1)
                    if not product_id:
                        description = ''
                        product_additional = product.get('product_additional', False)
                        if product_additional:
                            product_attributes = product_additional.get('attributes', False)
                            if product_attributes:
                                description = product_attributes.get('description', False)
                        error += "\nProduct Not found for - " +'['+ product_code +']'+ description if description else ''
                    product_qty = line.get('po_item_qty_confirmed')
                    product_unit_price = line.get('po_item_unit_price_confirmed')
                    if product_id:
                        line_vals.append((0, 0, {'product_id': product_id.id,
                                         'product_uom_qty': product_qty,
                                         'price_unit': product_unit_price,
                                         }))
            vals.update({'order_line': line_vals,
                         'external_so_id': external_so_id,
                         'external_origin': 'spring_system'
                         })
            existing_so = self.env['sale.order'].search([('external_so_id', '=', external_so_id)], limit=1)
            existing_order = spring_systems_so_obj.search([('spring_system_so_id', '=', external_so_id)], limit=1)
            if not existing_so:
                if not error:
                    sale_order = self.env['sale.order'].create(vals)
                    existing_order = spring_systems_so_obj.search([('spring_system_so_id', '=', external_so_id)], limit=1)
                    if existing_order:
                        existing_order.update({'sale_order_id': sale_order.id,
                                               'system_errors': '',
                                               'edi_850_data': str(each),
                                               'payment_term_id': vals.get('payment_term_id', False),
                                               })
                    else:
                        spring_systems_so_obj.create({
                            'spring_system_so_id': each.get('po_id', ''),
                            'spring_system_vendor_num': each.get('retailer_id', ''),
                            'spring_system_po_num': each.get('po_num', ''),
                            'status': 'draft',
                            'sale_order_id': sale_order.id,
                            'payment_term_id': vals.get('payment_term_id', ''),
                            'edi_850_data': str(each),
                            'configuration_id': self.id
                        })
                else:
                    existing_order = spring_systems_so_obj.search([('spring_system_so_id', '=', external_so_id)],
                                                                  limit=1)
                    if existing_order:
                        existing_order.update({
                                               'system_errors': error
                                               })
                    else:
                        spring_systems_so_obj.create({
                            'spring_system_so_id': each.get('po_id', False),
                            'spring_system_vendor_num': each.get('retailer_id', False),
                            'spring_system_po_num': each.get('po_num', False),
                            'status' : 'draft',
                            'payment_term_id': vals.get('payment_term_id', False),
                            'edi_850_data': str(each),
                            'system_errors': error,
                            'configuration_id': self.id
                        })
            elif existing_order:
                existing_order.update({'edi_850_data': str(each)})
