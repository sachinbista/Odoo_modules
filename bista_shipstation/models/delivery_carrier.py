# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
import logging

from dateutil import tz

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from .shipstation_request import ShipStationRequest
from odoo.exceptions import UserError, ValidationError
import base64
import requests
import json
from requests.auth import HTTPBasicAuth
UTC = tz.gettz('UTC')
PST = tz.gettz('PST')


class ProductPackaging(models.Model):
    _inherit = 'stock.package.type'

    height = fields.Float(string="Height")
    width = fields.Float(string="Width")
    packaging_length = fields.Float(string="Length")
    # length_uom_name = fields.Char(string="Size", default="inches")
#
#     # package_carrier_type = fields.Selection(selection_add=[('shipstation', 'Shipstation')])
#     shipstation_carrier_id = fields.Many2one('shipstation.delivery.carrier',
#                                           string='Shipstation Carrier')
#     shipstation_service_id = fields.Many2one('shipstation.carrier.service',
#                                           string='Carrier Service')
#     shipper_package_code = fields.Char('Carrier Code',related='shipstation_service_id.code')
#     # shipstation_account = fields.Many2one('shipstation.config', related="shipstation_carrier_id.account_id")


class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('shipstation', 'ShipStation')], ondelete={
        'shipstation': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    shipstation_production_api_key = fields.Char("Production API Key", groups="base.group_system",
                                                 help="Enter your API production key from ShipStation account")
    shipstation_production_api_secret = fields.Char("Production API Secret", groups="base.group_system",
                                                    help="Enter your API production secret from ShipStation account")
    shipstation_delivery_type = fields.Char('ShipStation Carrier Type')
    shipstation_default_service_id = fields.Many2one("shipstation.service", string="Default Service Level",
                                                     help="If not set, the less expensive available service level will be chosen.",
                                                     domain="[('shipstation_carrier', '=', shipstation_delivery_type)]")
    shipstation_weight_uom_id = fields.Many2one("uom.uom", domain=lambda self: [('id', 'in', [
        self.env.ref('uom.product_uom_gram').id, self.env.ref('uom.product_uom_oz').id,
        self.env.ref('uom.product_uom_lb').id])])
    add_ship_cost = fields.Boolean(string="Add Shipping Cost")
    store_id = fields.Many2one('shipstation.store')
    api_url = fields.Char(string='URL', tracking=True,
                          default="https://ssapi.shipstation.com")

    package_type_ship = fields.Many2one('stock.package.type', string="Package")
    carrier_code=fields.Selection([
        ('fedex', 'Fedex'),
        ('ups', 'UPS')], 'Package Type')

    def import_package_from_ship_station(self):
        for line in self:
            url='https://ssapi.shipstation.com/carriers/listpackages?carrierCode=' + line.carrier_code
            api_key = self.shipstation_production_api_key
            api_secret = self.shipstation_production_api_secret
            resp = requests.get(url, auth=HTTPBasicAuth(api_key,api_secret))
            if resp.status_code == 200:
                rec = json.loads(resp.text)
                for line in rec:
                    carrier_code=line.get('carrierCode')
                    name=line.get('name')
                    package_type_id=self.env['stock.package.type'].search([('name','=',name)])
                    if not package_type_id:
                        self.env['stock.package.type'].create({
                            'name':name,
                            'shipper_package_code':carrier_code
                        })
        return True



    def get_api_function(self, url, store=False, payload=False):
        """ Fetch response data based on URL using request GET. """
        if self.delivery_type == 'shipstation':
            api_key = self.shipstation_production_api_key
            api_secret = self.shipstation_production_api_secret
            data = "%s:%s" % (api_key, api_secret)
            encode_data = base64.b64encode(data.encode("utf-8"))
            authorization_data = "Basic %s" % (encode_data.decode("utf-8"))
            headers = {"Authorization": "%s" % authorization_data}
            try:
                response_data = request(method='GET', url=url, headers=headers, data=payload)
                return response_data
            except Exception as e:
                raise ValidationError(e)

    def import_dc_from_ship_station(self):
        """This function import delivery carriers from ShipStation"""
        url = self.api_url + "/carriers"

        response = self.get_api_function(url)
        if response.status_code != 200:
            desc = ("Error while fetching carriers - %s : %s" % (
                response.status_code, response.reason))
        shipstation_delivery_carrier = self.env['shipstation.delivery.carrier']
        try:
            responses = response.json()
            for response in responses:
                delivery_carrier = shipstation_delivery_carrier.search([('code', '=', response.get('code', False))])
                if not delivery_carrier:
                    shipstation_delivery_carrier.create(
                        {'name': response.get('name', False),
                         'code': response.get('code', False),
                         'account_number': response.get('accountNumber', False),
                         'shipping_provider_id': response.get('shippingProviderId',
                                                              False),
                         'balance': response.get('balance', False)
                         })

                else:
                    delivery_carrier.write({'balance': response.get('balance', False)})
        except Exception as e:
            desc = ("Error while fetching store - %s" % e)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Import Carriers Successfully!',
                'type': 'rainbow_man',
            }
        }

    def import_cs_from_ship_station(self):
        shipstation_carrier_service = self.env['shipstation.carrier.service']
        ship_log_line_dict = {'error': [], 'success': []}
        self.env.cr.execute("""SELECT distinct(code) FROM shipstation_delivery_carrier""")
        for codes in self.env.cr.fetchall():
            url = self.api_url + "/carriers/listservices?carrierCode=" + str(codes[0])
            response_data = self.get_api_function(url)
            if response_data.status_code != 200:
                desc = ("Error while fetching carriers - %s : %s" % (
                    response_data.status_code, response_data.reason))
                ship_log_line_dict['error'].append({'error_message': 'Carrier Service Import: %s' % desc})
            if response_data.status_code == 401:
                error_msg = 'Error response - ' + response_data.text + '. Please check the credentials'
                raise ValidationError(error_msg)
            try:
                for response in response_data.json():
                    carrier_id = self.env['shipstation.delivery.carrier'].search(
                        [('code', '=', response.get('carrierCode', False))]).id
                    delivery_carrier = shipstation_carrier_service.search(
                        [('code', '=', response.get('code', False)), ('delivery_carrier_id', '=', carrier_id)])
                    if not delivery_carrier:
                        shipstation_carrier_service.create(
                            {'name': response.get('name', False),
                             'code': response.get('code', False),
                             'carrier_code': response.get('carrierCode', False),
                             'domestic': response.get('domestic', False),
                             'international': response.get('international',
                                                           False),
                             'delivery_carrier_id': carrier_id
                             })

                        ship_log_line_dict['success'].append(
                            {'error_message': 'Carrier Service created: %s' % response.get('name', False)})

            except Exception as e:
                desc = ("Error while fetching Carrier Service - %s" % e)
                ship_log_line_dict['error'].append(
                    {'error_message': 'Exception error: %s' % desc})
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Import Services Successfully!',
                'img_url': 'bista_shipstation_connector/static/description/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def import_store_from_ship_station(self):
        """This function import store from ShipStation"""
        ir_model_obj = self.env['ir.model']
        model = ir_model_obj.search([('model', '=', 'shipstation.store')], limit=1)
        url = self.api_url + "/stores?stores?showInactive=false"
        # error_log_env = self.env['shipstation.error.log']
        shipstation_store = self.env['shipstation.store']
        state = 'error'
        # shipstation_log_id = error_log_env.create_update_log(
        #     shipstation_config_id=self,
        #     operation_type='import_store')
        ship_log_line_dict = {'error': [], 'success': []}
        response = self.get_api_function(url)
        if response.status_code != 200:
            desc = ("Error while fetching store - %s : %s" % (
                response.status_code, response.reason))
            ship_log_line_dict['error'].append(
                {'error_message': 'Import Store: %s' % desc})
        if response.status_code == 401:
            error_msg = 'Error response - ' + response.text + '. Please check the credentials'
            raise ValidationError(error_msg)
        try:
            responses = response.json()
            for res in responses:
                store = shipstation_store.search([('store_id', '=', res.get('storeId', False))])
                if not store:
                    shipstation_store.create({
                        'store_id': res.get('storeId', False),
                        'store_name': res.get('storeName', False),
                        'marketplace_id': res.get('marketplaceId', False),
                    })
                    ship_log_line_dict['success'].append(
                        {'error_message': 'Store Created: %s' % res.get('storeName', False)})
                else:
                    ship_log_line_dict['success'].append(
                        {'error_message': 'Store Already crated: %s' % res.get('storeName', False)})
                state = 'success'
        except Exception as e:
            desc = ("Error while fetching store - %s" % e)
            ship_log_line_dict['error'].append(
                {'error_message': 'Import Store: %s' % desc})
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Action Completed Successfully!',
                'img_url': 'bista_shipstation_connector/static/description/smile.svg',
                'type': 'rainbow_man',
            }
        }

    def shipstation_rate_shipment(self, order):
        sp = ShipStationRequest(self.sudo().shipstation_production_api_key,
                                self.sudo().shipstation_production_api_secret, self.log_xml)
        response = sp.rate_request(self, order.partner_shipping_id, order.warehouse_id.partner_id, order)
        # Return error message
        if response.get('error_message'):
            return {
                'success': False,
                'price': 0.0,
                'error_message': response.get('error_message'),
                'warning_message': False
            }

        # Update price with the order currency
        rate = response.get('rate')
        if order.currency_id.name == rate['currency']:
            price = float(rate['rate'])
        else:
            quote_currency = self.env['res.currency'].search([('name', '=', rate['currency'])], limit=1)
            price = quote_currency._convert(float(rate['rate']), order.currency_id, self.env.company,
                                            fields.Date.today())

        return {
            'success': True,
            'price': price,
            'error_message': False,
            'warning_message': response.get('warning_message', False),
            'rates': rate.get('rates', [])
        }

    def _shipstation_convert_weight(self, weight):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        weight = weight_uom_id._compute_quantity(weight, self.shipstation_weight_uom_id)
        if len(str(weight).split(".")[-1]) > 10:
            weight = round(weight, 2)
        return weight

    def shipstation_send_shipping(self, pickings):
        res = []
        sp = ShipStationRequest(self.sudo().shipstation_production_api_key,
                                self.sudo().shipstation_production_api_secret, self.log_xml)
        for picking in pickings.filtered(lambda l: l.state == "done" and not l.shipstation_order_id):
            result = sp.send_shipping(self, picking.partner_id, picking.picking_type_id.warehouse_id.partner_id,
                                      picking=picking)
            ss_order_id = result.get('orderId', False)
            ss_order_key = result.get('orderKey', False)
            if ss_order_id:
                picking.update({
                    'shipstation_order_id': ss_order_id,
                    'shipstation_order_key': ss_order_key
                })
            else:
                raise UserError("Couldn't place ShipStation Order.")
            res += [{'exact_price': 0.0, 'tracking_number': False}]
        return res

    def _generate_services(self, carrier, rates):
        services_name = {rate.get('serviceCode'): rate.get('serviceCode') for rate in rates}
        existing_services = self.env['shipstation.service'].search_read(
            [('name', 'in', list(services_name.keys())), ('shipstation_carrier', '=', carrier)], ['name'])
        for service_name in set([service['name'] for service in existing_services]) ^ set(services_name.keys()):
            self.env['shipstation.service'].create({
                'name': service_name,
                'service': services_name[service_name],
                'shipstation_carrier': carrier
            })

    @api.model
    def run_product_sync(self):
        # list all product in odoo, with to_sync = True
        # - to_sync = True when customer change product info
        # for each odoo product, find product in shipstation
        # update product in shipstation
        # update odoo product to_sync = False
        sr = False
        delivery_ids = self.search([('delivery_type', '=', 'shipstation')])
        for delivery in delivery_ids:
            if delivery.shipstation_production_api_key and delivery.shipstation_production_api_secret:
                sr = ShipStationRequest(delivery.sudo().shipstation_production_api_key,
                                        delivery.sudo().shipstation_production_api_secret, delivery.log_xml)
                if not sr:
                    _logger.warning("Skip run_product_sync due to no Shipping Methods for ShipStation found")
                    return
                products = self.env["product.product"].search(
                    [
                        ("to_sync", "=", True),
                        ("barcode", "!=", False),
                        ("hs_code", "!=", False),
                    ]
                )
                for product in products:
                    product_params = {"sku": product.barcode}
                    product_response = sr._make_api_request('/products', 'get', data=product_params, timeout=-1)
                    if not product_response or product_response.get("total") != 1:
                        _logger.warning("Unable to update product {}: No matching product found on ShipStation".format(
                            product.name))
                        product.to_sync = False
                        continue
                    update_params = product_response["products"][0]
                    update_params.update({"customsTariffNo": product.hs_code})
                    _logger.info("Syncing product with name: {}".format(product.name))
                    try:
                        product.to_sync = False
                        sr._make_api_request(
                            '/products/{}'.format(update_params.get("productId")),
                            'put',
                            data=update_params,
                            timeout=-1
                        )
                        product.message_post(body="HS Code has been synced to ShipStation.")
                    except UserError as e:
                        _logger.warning("Unable to sync product {}. Error found!".format(product.name))
                        continue

        return

    def _prepare_invoice_values(self, order, pickings):
        invoice_vals = {
            'ref': order.client_order_ref,
            'move_type': 'out_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': order.user_id.id,
            'narration': order.note,
            'partner_id': order.partner_invoice_id.id,
            'fiscal_position_id': order.fiscal_position_id and order.fiscal_position_id._get_fiscal_position(
                order.partner_id).id or False,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_reference': order.reference,
            'invoice_payment_term_id': order.payment_term_id.id,
            'partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
            'team_id': order.team_id.id,
            'campaign_id': order.campaign_id.id,
            'medium_id': order.medium_id.id,
            'source_id': order.source_id.id,
            'want_to_send_email': True,
            'picking_id': pickings.id,
        }
        return invoice_vals

    # @api.model
    # def run_shipstation_sync(self):
    #     print("run shiment calling .......................")
    #     delivery_ids = self.search([('delivery_type', '=', 'shipstation')])
    #     print("delivery_ids................",delivery_ids)
    #     sale_order_obj = self.env['sale.order']
    #     for delivery in delivery_ids:
    #         if delivery.shipstation_production_api_key and delivery.shipstation_production_api_secret:
    #             sr = ShipStationRequest(delivery.sudo().shipstation_production_api_key,
    #                                     delivery.sudo().shipstation_production_api_secret, delivery.log_xml)
    #             picking_ids = self.env['stock.picking'].search(
    #                 [('carrier_id', '=', False), ('state', '=', 'done'), ('carrier_tracking_ref', '=', False),
    #                  ('shipstation_order_id', '!=', False), ('picking_type_id.code', '=', 'outgoing')])
    #             last_call = self.env.context.get('lastcall', False)
    #             shipment_params = {
    #                 'sortBy': 'CreateDate',
    #                 'sortDir': 'ASC'
    #             }
    #             order_params = {
    #                 'sortBy': 'ModifyDate',
    #                 'sortDir': 'ASC'
    #             }
    #             if last_call:
    #                 last_call = (last_call - timedelta(hours=1)).replace(tzinfo=UTC).astimezone(PST).isoformat(sep='T',
    #                                                                                                            timespec='microseconds')
    #                 shipment_params['createDateStart'] = last_call
    #                 order_params['modifyDateStart'] = last_call
    #
    #             order_response = sr._make_api_request('/orders', 'get', data=order_params, timeout=-1)
    #             orders = order_response.get('orders', [])
    #             total = order_response.get('total', 0)
    #             if len(orders) < total:
    #                 order_params['pageSize'] = total - len(orders)
    #                 order_params['modifyDateStart'] = orders[-1]['modifyDate']
    #                 order_response = sr._make_api_request('/orders', 'get', data=order_params, timeout=-1)
    #                 orders += order_response.get('orders', [])
    #             merged_orders = None
    #             for order in orders:
    #                 if len(order['advancedOptions']['mergedIds']) > 0:
    #                     merged_orders = order['advancedOptions']['mergedIds']
    #                     merged_pickings = picking_ids.filtered(
    #                         lambda p: p.shipstation_order_id in [str(order) for order in merged_orders])
    #                     if merged_pickings:
    #                         merged_pickings.write({
    #                             'shipstation_order_id': str(order['orderId'])
    #                         })
    #                         msg = "Shipstation order merged with %s" % order['orderNumber']
    #                         for picking in merged_pickings:
    #                             picking.message_post(body=msg)
    #
    #             shipment_response = sr._make_api_request('/shipments', 'get', data=shipment_params, timeout=-1)
    #             shipments = shipment_response.get('shipments', [])
    #             print("shipments..........................",)
    #             total = shipment_response.get('total', 0)
    #             if len(shipments) < total:
    #                 shipment_params['pageSize'] = total - len(shipments)
    #                 shipment_params['createDateStart'] = shipments[-1]['createDate']
    #                 shipment_response = sr._make_api_request('/shipments', 'get', data=shipment_params, timeout=-1)
    #                 shipments += shipment_response.get('shipments', [])
    #             print("picking_ids..................",picking_ids)
    #             print("shipments..................",shipments)
    #             for shipment in shipments:
    #                 # if shipment['voided'] == False:
    #                 picking = picking_ids.filtered(lambda p: p.shipstation_order_id == str(shipment['orderId']))
    #                 if picking:
    #                     list_service_url = '/carriers/listservices?carrierCode=' + shipment['carrierCode']
    #                     carrier_name = sr._make_api_request(list_service_url, 'get', '', timeout=-1)
    #                     carrier_name = [x['name'] for x in carrier_name if x['code'] == shipment['serviceCode']]
    #                     picking.write({
    #                         'carrier_price': float(shipment['shipmentCost']) / len(picking),
    #                         'carrier_tracking_ref': shipment['trackingNumber'],
    #                         'carrier_id': delivery.id,
    #                         'shipstation_service': carrier_name[0] if carrier_name else '',
    #                         'shipstation_service_code': shipment['serviceCode']
    #                     })
    #                     if merged_orders and \
    #                             picking.group_id and len(picking.group_id) > 1:
    #                         sale_id = sale_order_obj.search([('name', '=', picking.group_id[0].name)])
    #                     else:
    #                         sale_id = sale_order_obj.search([('name', '=', picking.group_id.name)])
    #                     if sale_id and delivery and delivery.add_ship_cost:
    #                         # sale_id.freight_term_id and\
    #                         # not sale_id.freight_term_id.is_free_shipping and\
    #
    #                         sale_id.update({
    #                             'ss_quotation_carrier': shipment['carrierCode'],
    #                             'ss_quotation_service': carrier_name[0] if carrier_name else '',
    #                         })
    #                         carrier = delivery
    #                         amount = shipment['shipmentCost']
    #                     if not sale_id.is_free_shipping:
    #                         sale_id._create_delivery_line(carrier, amount)
    #                         delivery_lines = self.env['sale.order.line'].search(
    #                             [('order_id', 'in', sale_id.ids), ('is_delivery', '=', True)])
    #                         if delivery_lines:
    #                             delivery_lines.update({
    #                                 'name': sale_id.ss_quotation_service
    #                             })
    #
    #                     msg = _("Shipstation tracking number %s<br/>Cost: %.2f") % (
    #                     shipment['trackingNumber'], shipment['shipmentCost'],)
    #                     for pickings in picking:
    #                         pickings.message_post(body=msg)
    #                         if pickings.carrier_id or pickings.carrier_tracking_ref:
    #                             sale_id = pickings.sale_id
    #                             if pickings.origin and not sale_id:
    #                                 sale_id = sale_order_obj.search([('name', '=', pickings.origin)])
    #                             if not pickings.inv_created and sale_id:
    #                                 if sale_id.company_id.enable_auto_invoice:
    #                                     if sale_id.payment_term_id and sale_id.payment_term_id.auto_invoice:
    #                                         invoice_vals = self._prepare_invoice_values(sale_id)
    #                                         line_list = []
    #                                         invoice_count = sale_id.invoice_count
    #                                         for line in sale_id.order_line:
    #                                             if line.invoice_status == 'invoiced':
    #                                                 continue
    #
    #                                             # move_line_id = self.env['stock.move.line'].sudo().search(
    #                                             #     [('picking_id', '=', pickings.id),
    #                                             #      ('product_id', '=', line.product_id.id),
    #                                             #      ('move_id.sale_line_id', '=', line.id)])
    #
    #                                             line_dict = line._prepare_invoice_line()
    #                                             # for m_id in move_line_id:
    #                                             #     if not m_id:  # Product of type service
    #                                             #         line_dict.update({'quantity': line.product_uom_qty})
    #                                             #     else:
    #                                             #         if m_id.qty_done != 0:
    #                                             #             line_dict.update({'quantity': m_id.qty_done})
    #                                             #         elif m_id.product_uom_qty != 0:
    #                                             #             line_dict.update({'quantity': m_id.product_uom_qty})
    #                                             line_list.append((0, 0, line_dict))
    #                                             # if invoice_count == 0:
    #                                             #     # Because of this line, product Drop Ship cannot be added to invoice line.
    #                                             #     if line_dict['quantity'] > 0 and (
    #                                             #     line.is_delivery or line.product_id.type == "service"):
    #                                             #         line_list.append((0, 0, line_dict))
    #                                             # else:
    #                                             #     if line_dict['quantity'] > 0:
    #                                             #         line_list.append((0, 0, line_dict))
    #                                         if line_list and pickings.picking_type_code == 'outgoing':
    #                                             invoice_vals['invoice_line_ids'] = line_list
    #                                             invoice = self.env['account.move'].sudo().create(invoice_vals)
    #                                             # invoice.action_post()
    #
    #     return True




    # @api.model
    # def run_shipstation_sync(self):
    #     delivery_ids = self.search([('delivery_type', '=', 'shipstation')])
    #     sale_order_obj = self.env['sale.order']
    #     for delivery in delivery_ids:
    #         if delivery.shipstation_production_api_key and delivery.shipstation_production_api_secret:
    #             sr = ShipStationRequest(delivery.sudo().shipstation_production_api_key,
    #                                     delivery.sudo().shipstation_production_api_secret, delivery.log_xml)
    #             picking_ids = self.env['stock.picking'].search(
    #                 [('carrier_id', '=', False), ('state', '=', 'done'), ('carrier_tracking_ref', '=', False),
    #                  ('shipstation_order_id', '!=', False), ('picking_type_id.code', '=', 'outgoing')])
    #             last_call = self.env.context.get('lastcall', False)
    #             shipment_params = {
    #                 'sortBy': 'CreateDate',
    #                 'sortDir': 'ASC'
    #             }
    #             order_params = {
    #                 'sortBy': 'ModifyDate',
    #                 'sortDir': 'ASC'
    #             }
    #             if last_call:
    #                 last_call = (last_call - timedelta(hours=1)).replace(tzinfo=UTC).astimezone(PST).isoformat(sep='T',
    #                                                                                                            timespec='microseconds')
    #                 shipment_params['createDateStart'] = last_call
    #                 order_params['modifyDateStart'] = last_call
    #
    #             order_response = sr._make_api_request('/orders', 'get', data=order_params, timeout=-1)
    #             orders = order_response.get('orders', [])
    #             total = order_response.get('total', 0)
    #             if len(orders) < total:
    #                 order_params['pageSize'] = total - len(orders)
    #                 order_params['modifyDateStart'] = orders[-1]['modifyDate']
    #                 order_response = sr._make_api_request('/orders', 'get', data=order_params, timeout=-1)
    #                 orders += order_response.get('orders', [])
    #             merged_orders = None
    #             for order in orders:
    #                 if len(order['advancedOptions']['mergedIds']) > 0:
    #                     merged_orders = order['advancedOptions']['mergedIds']
    #                     merged_pickings = picking_ids.filtered(
    #                         lambda p: p.shipstation_order_id in [str(order) for order in merged_orders])
    #                     if merged_pickings:
    #                         merged_pickings.write({
    #                             'shipstation_order_id': str(order['orderId'])
    #                         })
    #                         msg = "Shipstation order merged with %s" % order['orderNumber']
    #                         for picking in merged_pickings:
    #                             picking.message_post(body=msg)
    #             for rec in picking_ids:
    #                 url = 'https://ssapi.shipstation.com/shipments?' + 'orderNumber=' + rec.name
    #                 resp = requests.get(url, auth=HTTPBasicAuth(delivery.shipstation_production_api_key,
    #                                                             delivery.shipstation_production_api_secret))
    #                 res_text = json.loads(resp.text)
    #                 if res_text.get('shipments'):
    #                     if res_text.get('shipments')[0].get('orderId') == int(rec.shipstation_order_id):
    #                         if res_text.get('shipments')[0].get('voided') == False:
    #                             dropship_ids = self.env['stock.picking'].search(
    #                                 [('carrier_id', '=', False), ('state', '=', 'done'),
    #                                  ('carrier_tracking_ref', '=', False),
    #                                  ('shipstation_order_id', '!=', False), ('picking_type_id.code', '=', 'incoming')])
    #                             picking = picking_ids.filtered(lambda p: p.shipstation_order_id == str(
    #                                 res_text.get('shipments')[0].get('orderId')))
    #                             dropship = dropship_ids.filtered(lambda p: p.shipstation_order_id == str(
    #                                 res_text.get('shipments')[0].get('orderId')))
    #                             if picking:
    #                                 list_service_url = '/carriers/listservices?carrierCode=' + \
    #                                                    res_text.get('shipments')[0].get('carrierCode')
    #                                 carrier_name = sr._make_api_request(list_service_url, 'get', '', timeout=-1)
    #                                 carrier_name = [x['name'] for x in carrier_name if
    #                                                 x['code'] == res_text.get('shipments')[0].get('serviceCode')]
    #
    #                                 picking.write({
    #                                     'carrier_price': float(res_text.get('shipments')[0].get('shipmentCost')) / len(
    #                                         picking),
    #                                     'carrier_tracking_ref': res_text.get('shipments')[0].get('trackingNumber'),
    #                                     'carrier_id': delivery.id,
    #                                     'shipstation_service': carrier_name[0] if carrier_name else '',
    #                                     'shipstation_service_code': res_text.get('shipments')[0].get('serviceCode')
    #                                 })
    #                                 if dropship:
    #                                     dropship.write({
    #                                         'carrier_price': float(
    #                                             res_text.get('shipments')[0].get('shipmentCost')) / len(dropship),
    #                                         'carrier_tracking_ref': res_text.get('shipments')[0].get('trackingNumber'),
    #                                         'carrier_id': delivery.id,
    #                                         'shipstation_service': carrier_name[0] if carrier_name else '',
    #                                         'shipstation_service_code': res_text.get('shipments')[0].get('serviceCode')
    #                                     })
    #                                     is_updated = self.env['sale.order'].shopify_update_order_status(
    #                                         picking.shopify_config_id, picking_ids=dropship)
    #                                 if merged_orders and \
    #                                         picking.group_id and len(picking.group_id) > 1:
    #                                     sale_id = sale_order_obj.search([('name', '=', picking.group_id[0].name)])
    #                                 else:
    #                                     sale_id = sale_order_obj.search([('name', '=', picking.group_id.name)])
    #                                 if sale_id and delivery and delivery.add_ship_cost:
    #                                     # sale_id.freight_term_id and\
    #                                     # not sale_id.freight_term_id.is_free_shipping and\
    #
    #                                     sale_id.update({
    #                                         'ss_quotation_carrier': res_text.get('shipments')[0].get('carrierCode'),
    #                                         'ss_quotation_service': carrier_name[0] if carrier_name else '',
    #                                     })
    #                                     carrier = delivery
    #                                     amount = res_text.get('shipments')[0].get('shipmentCost')
    #                                 if not sale_id.is_free_shipping:
    #                                     sale_id._create_delivery_line(carrier, amount)
    #                                     delivery_lines = self.env['sale.order.line'].search(
    #                                         [('order_id', 'in', sale_id.ids), ('is_delivery', '=', True)])
    #                                     if delivery_lines:
    #                                         delivery_lines.update({
    #                                             'name': sale_id.ss_quotation_service
    #                                         })
    #
    #                                 msg = _("Shipstation tracking number %s<br/>Cost: %.2f") % (
    #                                     res_text.get('shipments')[0].get('trackingNumber'),
    #                                     res_text.get('shipments')[0].get('shipmentCost'),)
    #                                 for pickings in picking:
    #                                     pickings.message_post(body=msg)
    #                                     if pickings.carrier_id or pickings.carrier_tracking_ref:
    #                                         sale_id = pickings.sale_id
    #                                         if pickings.origin and not sale_id:
    #                                             sale_id = sale_order_obj.search([('name', '=', pickings.origin)])
    #                                         if not pickings.inv_created and sale_id:
    #                                             if sale_id.company_id.enable_auto_invoice:
    #                                                 if sale_id.payment_term_id and sale_id.payment_term_id.auto_invoice:
    #                                                     delivery_lines = self.env['sale.order.line'].search(
    #                                                         [('order_id', '=', sale_id.id),
    #                                                          ('product_id.detailed_type', '=', 'service'),
    #                                                          ('qty_invoiced', '=', 0.0)])
    #                                                     invoice_vals = self._prepare_invoice_values(sale_id)
    #                                                     line_list = []
    #                                                     invoice_count = sale_id.invoice_count
    #                                                     for line in sale_id.order_line:
    #                                                         if line.invoice_status == 'invoiced':
    #                                                             continue
    #                                                         move_line_id = self.env['stock.move.line'].sudo().search(
    #                                                             [('picking_id', '=', picking.id),
    #                                                              ('product_id', '=', line.product_id.id),
    #                                                              ('move_id.sale_line_id', '=', line.id)])
    #                                                         if move_line_id:
    #                                                             line_dict = line._prepare_invoice_line()
    #                                                             qty_to_invoice = 0
    #                                                             for m_id in move_line_id:
    #                                                                 qty_to_invoice += m_id.qty_done
    #                                                             line_dict.update({'quantity': qty_to_invoice})
    #                                                             line_list.append((0, 0, line_dict))
    #                                                     for delivery_line in delivery_lines:
    #                                                         delivery_line_dict = delivery_line._prepare_invoice_line()
    #                                                         delivery_line_dict.update(
    #                                                             {'quantity': delivery_line.product_uom_qty})
    #                                                         line_list.append((0, 0, delivery_line_dict))
    #
    #                                                                 # for m_id in move_line_id:
    #                                                                 #     if not m_id:  # Product of type service
    #                                                                 #         line_dict.update({'quantity': line.product_uom_qty})
    #                                                                 #     else:
    #                                                                 #         if m_id.qty_done != 0:
    #                                                                 #             print("1111111111111111111111111111111111111111111")
    #                                                                 #             line_dict.update({'quantity': m_id.qty_done})
    #                                                                 #         elif m_id.product_uom_qty != 0:
    #                                                                 #             print("33333333333333333333333333333333333333333333")
    #                                                                 #             line_dict.update({'quantity': m_id.product_uom_qty})
    #                                                                 # line_list.append((0, 0, line_dict))
    #                                                                 # if invoice_count == 0:
    #                                                                 #     # Because of this line, product Drop Ship cannot be added to invoice line.
    #                                                                 #     if line_dict['quantity'] > 0 and (
    #                                                                 #             m_id or line.is_delivery or line.product_id.type == "service"):
    #                                                                 #         line_list.append((0, 0, line_dict))
    #                                                                 # else:
    #                                                                 #     if line_dict['quantity'] > 0 and m_id:
    #                                                                 #         line_list.append((0, 0, line_dict))
    #                                                     if line_list and picking.picking_type_code == 'outgoing':
    #                                                         invoice_vals['invoice_line_ids'] = line_list
    #                                                         invoice = self.env['account.move'].sudo().create(
    #                                                             invoice_vals)
    #                                                         invoice.action_post()
    #                                                         picking.inv_created = True


class ShipstationOrder(models.Model):
    _name = 'shipstation.store'
    _rec_name = 'store_name'

    store_id = fields.Char(string='Store Id')
    store_name = fields.Char(string='Store Name')
    marketplace_id = fields.Char(string='MarkerPlace ID')
    marketplace_name = fields.Char(string='MarkerPlace Name')
    acc_number = fields.Char(string='Account Number')
