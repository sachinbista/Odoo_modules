from odoo import fields, models, api,_
import requests
import json
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
from urllib.parse import parse_qs
from odoo.addons.bista_shipstation.models.shipstation_request import ShipStationRequest
from odoo import http
from odoo.http import request
from datetime import timedelta


class Binary(http.Controller):

    @http.route('/shipments', type='json', auth="public", methods=['POST'], csrf=False)
    def post_shipemts(self, **kwargs):
        res_data = request.httprequest.data
        data=json.loads(res_data)
        carrier_id = request.env['delivery.carrier'].sudo().search(
            [('delivery_type', '=', 'shipstation'), ('company_id', '=', request.env.company.id)], limit=1)
        sale_order_obj = request.env['sale.order']
        resp = requests.get(data['resource_url'],
                            auth=HTTPBasicAuth(carrier_id.shipstation_production_api_key,
                                               carrier_id.shipstation_production_api_secret))
        res_text = json.loads(resp.text)
        for delivery in carrier_id:
            if delivery.shipstation_production_api_key and delivery.shipstation_production_api_secret:
                sr = ShipStationRequest(delivery.sudo().shipstation_production_api_key,
                                        delivery.sudo().shipstation_production_api_secret, delivery.log_xml)
                picking_ids = request.env['stock.picking'].sudo().search([('name','=',res_text.get('shipments')[0].get('orderNumber'))])
                last_call = request.env.context.get('lastcall', False)
                shipment_params = {
                    'sortBy': 'CreateDate',
                    'sortDir': 'ASC'
                }
                order_params = {
                    'sortBy': 'ModifyDate',
                    'sortDir': 'ASC'
                }
                if last_call:
                    last_call = (last_call - timedelta(hours=1)).replace(tzinfo=UTC).astimezone(PST).isoformat(sep='T',
                                                                                                               timespec='microseconds')
                    shipment_params['createDateStart'] = last_call
                    order_params['modifyDateStart'] = last_call

                order_response = sr._make_api_request('/orders', 'get', data=order_params, timeout=-1)
                orders = order_response.get('orders', [])
                total = order_response.get('total', 0)
                if len(orders) < total:
                    order_params['pageSize'] = total - len(orders)
                    order_params['modifyDateStart'] = orders[-1]['modifyDate']
                    order_response = sr._make_api_request('/orders', 'get', data=order_params, timeout=-1)
                    orders += order_response.get('orders', [])
                merged_orders = None
                for order in orders:
                    if len(order['advancedOptions']['mergedIds']) > 0:
                        merged_orders = order['advancedOptions']['mergedIds']
                        merged_pickings = picking_ids.filtered(
                            lambda p: p.shipstation_order_id in [str(order) for order in merged_orders])
                        if merged_pickings:
                            merged_pickings.write({
                                'shipstation_order_id': str(order['orderId'])
                            })
                            msg = "Shipstation order merged with %s" % order['orderNumber']
                            for picking in merged_pickings:
                                picking.message_post(body=msg)

                shipments = res_text.get('shipments', [])
                total = res_text.get('total', 0)
                if len(shipments) < total:
                    shipment_params['pageSize'] = total - len(shipments)
                    shipment_params['createDateStart'] = shipments[-1]['createDate']
                    shipments += res_text.get('shipments', [])
                for shipment in shipments:
                    if res_text.get('shipments')[0].get('voided') == False:
                        list_service_url = '/carriers/listservices?carrierCode=' + shipment['carrierCode']
                        carrier_name = sr._make_api_request(list_service_url, 'get', '', timeout=-1)
                        carrier_name = [x['name'] for x in carrier_name if x['code'] == shipment['serviceCode']]
                        dropship_ids = request.env['stock.picking'].sudo().search(
                            [('carrier_id', '=', False), ('state', '=', 'done'),
                             ('carrier_tracking_ref', '=', False),
                             ('shipstation_order_id', '!=', False), ('picking_type_id.code', '=', 'incoming')])

                        dropship = dropship_ids.filtered(lambda p: p.shipstation_order_id == str(
                            res_text.get('shipments')[0].get('orderId')))
                        picking = picking_ids.filtered(lambda p: p.shipstation_order_id == str(shipment['orderId']))
                        if dropship:
                            dropship.write({
                                'carrier_price': float(
                                    res_text.get('shipments')[0].get('shipmentCost')) / len(dropship),
                                'carrier_tracking_ref': res_text.get('shipments')[0].get('trackingNumber'),
                                'carrier_id': delivery.id,
                                'shipstation_service': carrier_name[0] if carrier_name else '',
                                'shipstation_service_code': res_text.get('shipments')[0].get('serviceCode')
                            })
                            is_updated = request.env['sale.order'].sudo().shopify_update_order_status(
                                picking.shopify_config_id, picking_ids=dropship)
                        # if shipment['voided'] == False:
                        if picking:
                            picking.sudo().write({
                                'carrier_price': float(shipment['shipmentCost']) / len(picking),
                                'carrier_tracking_ref': shipment['trackingNumber'],
                                'carrier_id': delivery.id,
                                'shipstation_service': carrier_name[0] if carrier_name else '',
                                'shipstation_service_code': shipment['serviceCode']
                            })
                            # # -------- code is for create shipping for rithum platform start
                            # if picking.shipstation_order_id and picking.sale_id.rithum_config_id:
                            #     picking.sale_id.rithum_config_id.with_context(
                            #         ship_station_sync_picking=True).create_shipment_rithum_order(picking=picking)
                            # # ---------- code is for create shipping for rithum platform end
                            if merged_orders and \
                                    picking.group_id and len(picking.group_id) > 1:
                                sale_id = sale_order_obj.sudo().search([('name', '=', picking.group_id[0].name)])
                            else:
                                sale_id = sale_order_obj.sudo().search([('name', '=', picking.group_id.name)])
                            if sale_id and delivery and delivery.add_ship_cost:
                                # sale_id.freight_term_id and\
                                # not sale_id.freight_term_id.is_free_shipping and\

                                sale_id.sudo().update({
                                    'ss_quotation_carrier': shipment['carrierCode'],
                                    'ss_quotation_service': carrier_name[0] if carrier_name else '',
                                })
                                carrier = delivery
                                amount = shipment['shipmentCost']
                            if not sale_id.is_free_shipping:
                                sale_id._create_delivery_line(carrier, amount)
                                delivery_lines = request.env['sale.order.line'].sudo().search(
                                    [('order_id', 'in', sale_id.ids), ('is_delivery', '=', True)])
                                if delivery_lines:
                                    delivery_lines.update({
                                        'name': sale_id.ss_quotation_service
                                    })

                            msg = _("Shipstation tracking number %s<br/>Cost: %.2f") % (
                                shipment['trackingNumber'], shipment['shipmentCost'],)
                            for pickings in picking:
                                pickings.sudo().message_post(body=msg)
                                if pickings.carrier_id or pickings.carrier_tracking_ref:
                                    sale_id = pickings.sale_id
                                    if pickings.origin and not sale_id:
                                        sale_id = sale_order_obj.sudo().search([('name', '=', pickings.origin)])
                                    if not pickings.inv_created and sale_id:
                                        if sale_id.company_id.enable_auto_invoice:
                                            if sale_id.payment_term_id and sale_id.payment_term_id.auto_invoice:
                                                delivery_lines = request.env['sale.order.line'].sudo().search(
                                                    [('order_id', '=', sale_id.id),
                                                     ('product_id.detailed_type', '=', 'service'),
                                                     ('qty_invoiced', '=', 0.0)])
                                                invoice_vals = request.env['delivery.carrier'].sudo()._prepare_invoice_values(sale_id,pickings)
                                                line_list = []
                                                invoice_count = sale_id.invoice_count
                                                for line in sale_id.order_line:
                                                    if line.invoice_status == 'invoiced':
                                                        continue
                                                    move_line_id = request.env['stock.move.line'].sudo().search(
                                                        [('picking_id', '=', picking.id),
                                                         ('product_id', '=', line.product_id.id),
                                                         ('move_id.sale_line_id', '=', line.id)])
                                                    if move_line_id:
                                                        line_dict = line.sudo()._prepare_invoice_line()
                                                        qty_to_invoice = 0
                                                        for m_id in move_line_id:
                                                            qty_to_invoice += m_id.qty_done
                                                        line_dict.update({'quantity': qty_to_invoice})
                                                        line_list.append((0, 0, line_dict))
                                                for delivery_line in delivery_lines:
                                                    delivery_line_dict = delivery_line.sudo()._prepare_invoice_line()
                                                    delivery_line_dict.update(
                                                        {'quantity': delivery_line.product_uom_qty})
                                                    line_list.append((0, 0, delivery_line_dict))

                                                    # for m_id in move_line_id:
                                                    #     if not m_id:  # Product of type service
                                                    #         line_dict.update({'quantity': line.product_uom_qty})
                                                    #     else:
                                                    #         if m_id.qty_done != 0:
                                                    #             print("1111111111111111111111111111111111111111111")
                                                    #             line_dict.update({'quantity': m_id.qty_done})
                                                    #         elif m_id.product_uom_qty != 0:
                                                    #             print("33333333333333333333333333333333333333333333")
                                                    #             line_dict.update({'quantity': m_id.product_uom_qty})
                                                    # line_list.append((0, 0, line_dict))
                                                    # if invoice_count == 0:
                                                    #     # Because of this line, product Drop Ship cannot be added to invoice line.
                                                    #     if line_dict['quantity'] > 0 and (
                                                    #             m_id or line.is_delivery or line.product_id.type == "service"):
                                                    #         line_list.append((0, 0, line_dict))
                                                    # else:
                                                    #     if line_dict['quantity'] > 0 and m_id:
                                                    #         line_list.append((0, 0, line_dict))
                                                if line_list and picking.picking_type_code == 'outgoing':
                                                    invoice_vals['invoice_line_ids'] = line_list
                                                    invoice = request.env['account.move'].sudo().create(
                                                        invoice_vals)
                                                    invoice.action_post()
                                                    picking.inv_created = True

        return json.dumps({"message": "Api called Successfully", "status_code": 200})
