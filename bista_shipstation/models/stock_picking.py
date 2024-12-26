# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api,_
import requests
import json
from requests.auth import HTTPBasicAuth
from odoo.addons.bista_shipstation.models.shipstation_request import ShipStationRequest
from datetime import timedelta


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        sale_id = self.mapped('sale_line_id').mapped('order_id')[:1]
        if sale_id:
            shipstation_delivery = self.env['delivery.carrier'].search([('delivery_type', '=', 'shipstation')]).mapped(
                'product_id')
            shipstation_service = sale_id.order_line.filtered(
                lambda l: l.is_delivery and l.product_id.id in shipstation_delivery.ids)[:1].name
            res.update({'shipstation_service': shipstation_service, 'carrier_id': ''})
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipstation_order_id = fields.Char("ShipStation Order Reference", copy=False)
    shipstation_order_key = fields.Char('ShipStation Order Key', copy=False)
    shipstation_service = fields.Char("ShipStation Service")
    shipstation_service_code = fields.Char("ShipStation Service Code")
    delivery_type = fields.Selection(related='carrier_id.delivery_type')

    def action_shipment_sync(self):
        for pic_id in self:
            delivery_ids = self.env['delivery.carrier'].search(
                [('delivery_type', '=', 'shipstation'), ('company_id', '=', pic_id.env.company.id)])
            sale_order_obj = self.env['sale.order']
            for delivery in delivery_ids:
                if delivery.shipstation_production_api_key and delivery.shipstation_production_api_secret:
                    sr = ShipStationRequest(delivery.sudo().shipstation_production_api_key,
                                            delivery.sudo().shipstation_production_api_secret, delivery.log_xml)
                    picking_ids = pic_id

                    last_call = pic_id.env.context.get('lastcall', False)
                    shipment_params = {
                        'sortBy': 'CreateDate',
                        'sortDir': 'ASC'
                    }
                    order_params = {
                        'sortBy': 'ModifyDate',
                        'sortDir': 'ASC'
                    }
                    if last_call:
                        last_call = (last_call - timedelta(hours=1)).replace(tzinfo=UTC).astimezone(PST).isoformat(
                            sep='T',
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
                    for rec in picking_ids:
                        url = 'https://ssapi.shipstation.com/shipments?' + 'orderNumber=' + rec.name
                        resp = requests.get(url, auth=HTTPBasicAuth(delivery.shipstation_production_api_key,
                                                                    delivery.shipstation_production_api_secret))
                        res_text = json.loads(resp.text)
                        if res_text.get('shipments'):
                            for ship_id in res_text.get('shipments'):
                                if ship_id.get('orderId') == int(rec.shipstation_order_id):
                                    if ship_id.get('voided') == False:
                                        dropship_ids = self.env['stock.picking'].sudo().search(
                                            [ ('state', '=', 'done'),
                                             ('picking_type_id.code', '=', 'incoming')])

                                        picking = picking_ids.filtered(lambda p: p.shipstation_order_id == str(
                                            ship_id.get('orderId')))
                                        dropship = dropship_ids.filtered(lambda p: p.shipstation_order_id == str(
                                            ship_id.get('orderId')))
                                        if picking:
                                            list_service_url = '/carriers/listservices?carrierCode=' + \
                                                               ship_id.get('carrierCode')
                                            carrier_name = sr._make_api_request(list_service_url, 'get', '', timeout=-1)
                                            carrier_name = [x['name'] for x in carrier_name if
                                                            x['code'] == ship_id.get('serviceCode')]

                                            picking.write({
                                                'carrier_price': float(ship_id.get('shipmentCost')) / len(
                                                    picking),
                                                'carrier_tracking_ref': ship_id.get('trackingNumber'),
                                                'carrier_id': delivery.id,
                                                'shipstation_service': carrier_name[0] if carrier_name else '',
                                                'shipstation_service_code': ship_id.get('serviceCode')
                                            })
                                            if dropship:
                                                dropship.write({
                                                    'carrier_price': float(
                                                        ship_id.get('shipmentCost')) / len(dropship),
                                                    'carrier_tracking_ref': ship_id.get('trackingNumber'),
                                                    'carrier_id': delivery.id,
                                                    'shipstation_service': carrier_name[0] if carrier_name else '',
                                                    'shipstation_service_code': ship_id.get('serviceCode')
                                                })
                                                is_updated = self.env['sale.order'].shopify_update_order_status(
                                                    picking.shopify_config_id, picking_ids=dropship)
                                            if merged_orders and \
                                                    picking.group_id and len(picking.group_id) > 1:
                                                sale_id = sale_order_obj.search(
                                                    [('name', '=', picking.group_id[0].name)])
                                            else:
                                                sale_id = sale_order_obj.search([('name', '=', picking.group_id.name)])
                                            if sale_id and delivery and delivery.add_ship_cost:
                                                # sale_id.freight_term_id and\
                                                # not sale_id.freight_term_id.is_free_shipping and\

                                                sale_id.update({
                                                    'ss_quotation_carrier': ship_id.get('carrierCode'),
                                                    'ss_quotation_service': carrier_name[0] if carrier_name else '',
                                                })
                                                carrier = delivery
                                                amount = ship_id.get('shipmentCost')
                                            if not sale_id.is_free_shipping:
                                                sale_id._create_delivery_line(carrier, amount)
                                                delivery_lines = self.env['sale.order.line'].search(
                                                    [('order_id', 'in', sale_id.ids), ('is_delivery', '=', True)])
                                                if delivery_lines:
                                                    delivery_lines.update({
                                                        'name': sale_id.ss_quotation_service
                                                    })

                                            msg = _("Shipstation tracking number %s<br/>Cost: %.2f") % (
                                                ship_id.get('trackingNumber'),
                                                ship_id.get('shipmentCost'),)
                                            for pickings in picking:
                                                pickings.message_post(body=msg)
                                                if pickings.carrier_id or pickings.carrier_tracking_ref:
                                                    sale_id = pickings.sale_id
                                                    if pickings.origin and not sale_id:
                                                        sale_id = sale_order_obj.search(
                                                            [('name', '=', pickings.origin)])
                                                    if not pickings.inv_created and sale_id:
                                                        if sale_id.company_id.enable_auto_invoice:
                                                            if sale_id.payment_term_id and sale_id.payment_term_id.auto_invoice:
                                                                delivery_lines = self.env['sale.order.line'].search(
                                                                    [('order_id', '=', sale_id.id),
                                                                     ('product_id.detailed_type', '=', 'service'),
                                                                     ('qty_invoiced', '=', 0.0)])
                                                                invoice_vals = self._prepare_invoice_values(sale_id)
                                                                line_list = []
                                                                invoice_count = sale_id.invoice_count
                                                                for line in sale_id.order_line:
                                                                    if line.invoice_status == 'invoiced':
                                                                        continue
                                                                    move_line_id = self.env[
                                                                        'stock.move.line'].sudo().search(
                                                                        [('picking_id', '=', picking.id),
                                                                         ('product_id', '=', line.product_id.id),
                                                                         ('move_id.sale_line_id', '=', line.id)])
                                                                    if move_line_id:
                                                                        line_dict = line._prepare_invoice_line()
                                                                        qty_to_invoice = 0
                                                                        for m_id in move_line_id:
                                                                            qty_to_invoice += m_id.qty_done
                                                                        line_dict.update({'quantity': qty_to_invoice})
                                                                        line_list.append((0, 0, line_dict))
                                                                for delivery_line in delivery_lines:
                                                                    delivery_line_dict = delivery_line._prepare_invoice_line()
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
                                                                    invoice = self.env['account.move'].sudo().create(
                                                                        invoice_vals)
                                                                    invoice.action_post()
                                                                    picking.inv_created = True

    def _send_confirmation_email(self):
        res = super(StockPicking, self)._send_confirmation_email()
        self.user_id=self.env.uid
        carrier_id = self.env['delivery.carrier'].search(
            [('delivery_type', '=', 'shipstation'), ('company_id', '=', self.company_id.id)], limit=1)
        if carrier_id and self.picking_type_id.code == 'outgoing' and not self.carrier_id:
            if not self.picking_type_id.is_subcontractor:
                url = 'https://ssapi.shipstation.com/orders?' + 'orderNumber=' + self.name
                resp = requests.get(url, auth=HTTPBasicAuth(carrier_id.shipstation_production_api_key,
                                                            carrier_id.shipstation_production_api_secret))
                res_text = json.loads(resp.text)
                if res_text.get('orders') and res_text.get('orders')[0].get('advancedOptions').get('storeId') == int(carrier_id.store_id.store_id):
                    pass
                else:
                    carrier_id.shipstation_send_shipping(self)
        elif self.carrier_id and self.picking_type_id.code == 'outgoing':
            pass
        return res


class StockPickingType(models.Model):
    _inherit='stock.picking.type'

    is_subcontractor=fields.Boolean('Is Subcontractor')

