# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

# carrier_tracking_ref
from odoo import models, fields, api, _
from odoo.addons.bista_shipstation.models.shipstation_request import ShipStationRequest as ShipStationreq
from odoo.addons.bista_auto_invoice.models.stock_picking import StockInherit as sp
import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import timedelta
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _pre_action_done_hook(self):
        for sale_picking in self.filtered(lambda pick: pick.sale_id.rithum_config_id):
            if not sale_picking.sale_id.rithum_warning_accepted:
                status, updated_lines = sale_picking.sale_id.rithum_config_id.check_rithum_order_status(sale_picking)
                if status == 'cancelled':
                    raise ValidationError(_("You can not validate order, order is cancelled in Rithum."))
                elif status == 'cancelled_line':
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'rithum.order.sync.wizard',
                        'target': 'new',
                        'context': {'updated_lines': updated_lines}
                    }
        res = super()._pre_action_done_hook()
        return res

    def _action_done(self):
        # context = dict(self._context) or {}
        has_non_invoiced_lines = self.has_non_invoiced_lines()
        # if context.get('show_confirm', False) and has_non_invoiced_lines:
        #     self.post_non_invoiced_message(self.sale_id)
        #     return {
        #         'name': _('Non Invoiced Warning'),
        #         'type': 'ir.actions.act_window',
        #         'view_mode': 'form',
        #         'res_model': 'transfer.validate.confirm',
        #         'res_id': self.env['transfer.validate.confirm'].create({'picking_id': self.id}).id,
        #         'target': 'new'
        #     }

        res = super(sp, self)._action_done()

        inv_mail_template = self.env.ref('account.email_template_edi_invoice',
                                         raise_if_not_found=False)
        sale_order_obj = self.env['sale.order']
        for picking in self:
            sale_id = picking.sale_id
            if picking.origin and not sale_id:
                sale_id = sale_order_obj.search([('name', '=', picking.origin)])
            if picking.carrier_id or picking.carrier_tracking_ref:
                if not picking.inv_created and sale_id:
                    if sale_id.company_id.enable_auto_invoice:
                        if sale_id.payment_term_id and sale_id.payment_term_id.auto_invoice:
                            delivery_lines = self.env['sale.order.line'].search(
                                [('order_id', '=', sale_id.id), ('product_id.detailed_type', '=', 'service'),
                                 ('qty_invoiced', '=', 0.0)])
                            invoice_vals = self._prepare_invoice_values(sale_id)
                            line_list = []
                            invoice_count = sale_id.invoice_count
                            for line in sale_id.order_line:
                                if line.invoice_status == 'invoiced':
                                    continue

                                move_line_id = self.env['stock.move.line'].sudo().search(
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
                                delivery_line_dict.update({'quantity': delivery_line.product_uom_qty})
                                line_list.append((0, 0, delivery_line_dict))
                                # if invoice_count == 0:
                                #     if line_dict['quantity'] > 0 and (
                                #             m_id or line.is_delivery or line.product_id.type == "service"):
                                #         line_list.append((0, 0, line_dict))
                                # else:
                                #     if line_dict['quantity'] > 0 and m_id:
                                #         line_list.append((0, 0, line_dict))
                            if line_list and picking.picking_type_code == 'outgoing':
                                if picking.sale_id.rithum_config_id:

                                    if (picking.carrier_id and picking.carrier_tracking_ref):
                                        picking.sale_id.rithum_config_id.with_context(
                                            manual_validate_picking=True).create_shipment_rithum_order(picking=picking)
                                        # Method is in-comment if client want auto cancel order line on no-backorder on tirhum
                                        # cancel_move_ids = picking.move_ids.filtered(
                                        #     lambda move: move.state == 'cancel')
                                        # picking.sale_id.rithum_config_id.cancel_rithum_order_item(
                                        #     sale_id=picking.sale_id, cancel_move_ids=cancel_move_ids)

                                invoice_vals['invoice_line_ids'] = line_list
                                invoice = self.env['account.move'].sudo().create(invoice_vals)
                                invoice.action_post()
                                lang = False
                                if inv_mail_template:
                                    lang = inv_mail_template._render_lang(invoice.ids)[invoice.id]
                                emails = set(partner['email'] for partner in picking.sale_id.partner_id.child_ids if
                                             partner.email)
                                inv_mail_template.write({'email_to': ','.join(emails)})

                                ctx = dict(
                                    mark_invoice_as_sent=True,
                                    active_ids=invoice.ids,
                                    custom_layout="mail.mail_notification_paynow",
                                    model_description=invoice.with_context(lang=lang).type_name,
                                    force_email=True,
                                    default_res_model='account.move',
                                    default_use_template=bool(inv_mail_template))
                                values = {
                                    'model': 'account.move',
                                    'res_id': invoice.id,
                                    'template_id': inv_mail_template and inv_mail_template.id or False,
                                    'composition_mode': 'comment',
                                }
                                # if invoice.payment_state != "not_paid":
                                wizard = self.env['account.invoice.send'].with_context(ctx).create(values)
                                wizard._compute_composition_mode()
                                # wizard.onchange_template_id()
                                # wizard.onchange_is_email()
                                wizard._send_email()
                                # Empty email_to to prevent sending mail to wrong people
                                inv_mail_template.write({'email_to': ""})
                                picking.inv_created = True
                        else:
                            if picking.picking_type_code == 'outgoing':
                                if has_non_invoiced_lines:
                                    self.post_non_invoiced_message(sale_id)
                                    # self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                                    #     'title': _("Warning"),
                                    #     'sticky': False,
                                    #     'message': _('Some of the products you are attempting to deliver have not been fully invoiced and fully paid for. And message was logged to the group.')
                                    # })
        return res


    def action_shipment_sync(self):
        for pic_id in self:
            delivery_ids = self.env['delivery.carrier'].search(
                [('delivery_type', '=', 'shipstation'), ('company_id', '=', pic_id.env.company.id)])
            sale_order_obj = self.env['sale.order']
            for delivery in delivery_ids:
                if delivery.shipstation_production_api_key and delivery.shipstation_production_api_secret:
                    sr = ShipStationreq(delivery.sudo().shipstation_production_api_key,
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
                                            [('state', '=', 'done'),
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
                                            # -------- code is for create shipping for rithum platform start
                                            if rec.shipstation_order_id and rec.sale_id.rithum_config_id:
                                                rec.sale_id.rithum_config_id.with_context(ship_station_sync_picking=True).create_shipment_rithum_order(picking=rec)
                                            # ---------- code is for create shipping for rithum platform end
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




