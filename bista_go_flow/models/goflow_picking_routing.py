# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import requests
import json
import logging
import base64
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    goflow_store_id = fields.Many2one('goflow.store',copy=False)

    state = fields.Selection(
        selection=[
            ('draft', "Quotation"),
            ('sent', "Quotation Sent"),
            ('need_to_review', "Need to Review"),
            ('hold', "On Hold"),
            ('sale', "Sales Order"),
            ('done', "Locked"),
            ('cancel', "Cancelled"),
        ],
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')

    goflow_hold_reason = fields.Text("",copy=False)
    # shipping details
    goflow_customer_name = fields.Char("",copy=False)
    goflow_company = fields.Char("",copy=False)
    goflow_street1 = fields.Char("",copy=False)
    goflow_street2 = fields.Char("",copy=False)
    goflow_city = fields.Char("",copy=False)
    goflow_state = fields.Char("",copy=False)
    goflow_zip_code = fields.Char("",copy=False)
    goflow_country_code = fields.Char("",copy=False)
    goflow_email = fields.Char("",copy=False)
    goflow_phone = fields.Char("",copy=False)

    goflow_order_date = fields.Datetime()

    # shipment details
    goflow_shipment_type = fields.Selection([
        ("small_parcel", "Small Parcel"),
        ("ltl", "LTL"),
        ("messenger", "Messenger"),
        ("pickup", "Pickup")], copy=False, string="Shipment Type")
    goflow_carrier = fields.Char(copy=False, string="Carrier")
    goflow_shipping_method = fields.Char(copy=False, string="Shipping Method")
    goflow_scac = fields.Char(copy=False, string="SCAC")
    goflow_shipped_at = fields.Char(copy=False, string="Shipped at")
    goflow_currency_code = fields.Char(copy=False, string="Currency Code")
    goflow_order_status = fields.Char(string='Goflow Order Status')
    goflow_warehouse = fields.Char(string="Goflow Warehouse", copy=False)
    goflow_order_no = fields.Char(string="Goflow Order No", copy=False)
    goflow_po_no = fields.Char(string="Goflow PO No", copy=False)

    # carrier_id = fields.Many2one("delivery.carrier")
    # shipping_account = fields.Char()

    # @api.onchange('partner_id')
    # def set_carrier_n_account(self):
    #     if self.partner_id:
    #         self.carrier_id = self.partner_id.property_delivery_carrier_id
    #         self.shipping_account = self.partner_id.shipping_account
    #     if not self.partner_id:
    #         self.carrier_id = False
    #         self.shipping_account = ""

    def _prepare_invoice(self):
        """
        Override the original method to add 'warehouse_id' to the invoice creation.
        """
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'warehouse_id': self.warehouse_id.id,
        })
        return res

    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        for rec in self:
            goflow_shipment_type = rec.goflow_shipment_type
            picking_ids = rec.picking_ids
            picking_ids.rpa_process_priority = 2 if not goflow_shipment_type or goflow_shipment_type == 'ltl' else 1
            for pick in picking_ids:
                if pick.intercom_sale_order_id or pick.sale_id:
                    pick.goflow_order_id = pick.sale_id.id or pick.intercom_sale_order_id.id
                else:
                    pick.goflow_order_id = ''

        return res

    # get / fetch routing request
    def go_flow_fetch_shipment_routing_request(self):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)

        stock_pickings = self.env['stock.picking'].search([('goflow_routing_status','=','routing_requested')])
        for picking in stock_pickings:
            sale_id = picking.sale_id if picking.sale_id else picking.sudo().intercom_sale_order_id
            if sale_id:
                goflow_order = self.env['goflow.order'].search([('sale_order_id','=',sale_id.id)])
                # goflow_order_id = "3642"
                if go_flow_instance_obj and goflow_order:
                    url = f"/v1/orders/{goflow_order.goflow_order_id}/shipment-routing-request"
                    response = go_flow_instance_obj._send_goflow_request('get', url)

                    if response.status_code == 200:
                        picking.goflow_routing_status = 'routing_received'
                        
                        # goflow shipment details
                        # picking.goflow_shipment_type = ''
                        # picking.goflow_carrier = response['response']['carrier']['scac'] if response.get('response') else ''
                        # picking.goflow_shipping_method = ''
                        # picking.goflow_currency_code = ''
                        picking.goflow_scac = response['response']['carrier']['scac'] if response.get('response') else ''
                        sale_id.goflow_scac = response['response']['carrier']['scac'] if response.get('response') else ''

                        # calling get document_urls API
                        picking.goflow_get_order_document_urls(pack_box=False)

                        # picking.goflow_routing_request_enable = False
                        
                        response = response.json()
                    else:
                        picking.goflow_routing_status = 'routing_received'
                        response = response.json()

                        # check for 48hr
                        picking.check_n_reset_routing_status()

    # cancel order
    def _action_cancel(self):
        res = super(SaleOrder, self)._action_cancel()
        if not self._context.get('cancelled_from_goflow'):
            self.go_flow_cancel_sale_order()
        return res

    def go_flow_cancel_sale_order(self):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        if go_flow_instance_obj and go_flow_instance_obj.cancel_goflow_order:
            goflow_order = self.env['goflow.order'].search([('sale_order_id','=',self.id)], limit=1)
            url = f"/v1/orders/{goflow_order.goflow_order_id}/cancellation"
            data = {
                "notify_store": True,
                "reason": "cannot_fulfill"
            }
            response = go_flow_instance_obj._send_goflow_request('post', url, payload=data)

    def set_order_on_hold(self):
        goflow_order = self.env['goflow.order'].search([('sale_order_id','=',self.id)], limit=1)
        if goflow_order:
            goflow_order.goflow_set_order_hold()



    def unhold_order(self):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True),
                                                                        ('state', '=', 'done')], limit=1)
        if go_flow_instance_obj:
            if self.state == 'hold':
                goflow_orders = self.env['goflow.order'].search(
                    [('sale_order_id', '=', self.id)])
                url = f"/v1/orders?filters[id]={goflow_orders.goflow_order_id}"
                response = go_flow_instance_obj._send_goflow_request('get', url)
                if response and response.status_code == 200:
                    response_json = response.json()
                    order_json = response_json.get('data', [])
                    if not order_json:
                        goflow_orders.sale_order_id.sudo().action_cancel()
                        return
                    status = order_json[0].get('status', '')
                    if not status:
                        goflow_orders.sale_order_id.sudo().action_cancel()
                    if status == 'on_hold':
                        goflow_orders.sale_order_id.sudo().write({'state': 'hold'})
                    elif status == 'need_to_review':
                        goflow_orders.sale_order_id.sudo().write({'state': 'need_to_review'})
                    elif status not in ('on_hold', 'need_to_review','canceled'):
                        goflow_orders.sale_order_id.sudo().action_confirm()
                    elif status == 'canceled':
                        goflow_orders.sale_order_id.sudo().with_context(disable_cancel_warning=True).action_cancel()

                    goflow_orders.check_order_status = True

    def go_flow_check_order_status(self):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True),
                                                                        ('state', '=', 'done')], limit=1)
        if go_flow_instance_obj:
            sale_draft_orders = self.env['sale.order'].search([('state','=','draft'), ('external_origin', '=', 'go_flow')])
            if sale_draft_orders:
                goflow_orders = self.env['goflow.order'].search([('sale_order_id', 'in', sale_draft_orders.ids), ('check_order_status', '!=', True)],limit=10, order='id asc')
                for order in goflow_orders:
                    url = f"/v1/orders?filters[id]={order.goflow_order_id}"
                    response = go_flow_instance_obj._send_goflow_request('get', url)
                    if response and response.status_code == 200:
                        response_json = response.json()
                        order_json = response_json.get('data', [])
                        if not order_json:
                            order.sale_order_id.sudo().action_cancel()
                            continue
                        status = order_json[0].get('status', '')
                        # if not status:
                        #     order.sale_order_id.sudo().action_cancel()
                        if status == 'on_hold':
                            order.sale_order_id.sudo().write({'state': 'hold'})
                        elif status in ('ready_for_pickup', 'shipped'):
                            order.sale_order_id.sudo().action_confirm()
                        elif status == 'canceled':
                            order.sale_order_id.sudo().action_cancel()
                        order.check_order_status = True


    def go_flow_check_need_to_review(self, filter=None, go_flow_order_id=False):
        go_flow_instance_obj = self._get_active_goflow_instance()
        if go_flow_instance_obj:
            if go_flow_instance_obj.sync_order_review_filter:
                filter = go_flow_instance_obj.sync_order_review_filter
            try:
                url = self._get_goflow_url(go_flow_instance_obj, 'need_to_review', filter, go_flow_order_id)
                response = go_flow_instance_obj._send_goflow_request('get', url)
                self._process_goflow_response(response, 'need_to_review', go_flow_instance_obj)
            except Exception as e:
                _logger.error(f"An error occurred while processing orders for review: {e}")

    def go_flow_check_need_to_cancel(self, filter=None, go_flow_order_id=False):
        go_flow_instance_obj = self._get_active_goflow_instance()
        if go_flow_instance_obj:
            if go_flow_instance_obj.sync_order_cancel_filter:
                filter = go_flow_instance_obj.sync_order_cancel_filter
            try:
                url = self._get_goflow_url(go_flow_instance_obj, 'canceled', filter, go_flow_order_id)
                response = go_flow_instance_obj._send_goflow_request('get', url)
                self._process_goflow_response(response, 'cancel', go_flow_instance_obj)
            except Exception as e:
                _logger.error(f"An error occurred while processing canceled orders: {e}")

    def _get_active_goflow_instance(self):
        return self.env['goflow.configuration'].search(
            [('active', '=', True), ('goflow_order_review', '=', True), ('state', '=', 'done')], limit=1)

    def _get_goflow_url(self, go_flow_instance_obj, status, filter, go_flow_order_id=False):
        if go_flow_order_id:
            return f"/v1/orders?filters[id]={go_flow_order_id}&filters[status]={status}"
        elif filter:
            return '/v1/orders' + filter
        else:
            filter_date = go_flow_instance_obj.goflow_order_review_sync_date or datetime.now()
            zero_time = self._get_date_filter(go_flow_instance_obj, filter_date)
            if status == 'canceled':
                return f"/v1/orders?sort=id&sort_direction=asc&filters[status]={status}&filters[date:gte]={zero_time}"
            elif status == 'need_to_review':
                # introduced on_hold state orders too for in review orders cron as per requirement
                return f"/v1/orders?sort=id&sort_direction=asc&filters[status]={status}&filters[status]=on_hold&filters[date:gte]={zero_time}"

    def _process_goflow_response(self, response, state, go_flow_instance_obj):
        if response and response.status_code == 200:
            goflow_order_response = response.json()
            orders = goflow_order_response.get("data", [])
            next_orders = goflow_order_response.get("next", '')
            if orders:
                self._sale_write_status(orders, state)
            if next_orders:
                filter = next_orders.split('v1/orders')
                if state == 'cancel':
                    go_flow_instance_obj.sync_order_cancel_filter = filter[1]
                    # self.go_flow_check_need_to_cancel(filter=filter[1])
                elif state == 'need_to_review':
                    go_flow_instance_obj.sync_order_review_filter = filter[1]
                    # self.go_flow_check_need_to_review(filter=filter[1])
            else:
                if state == 'cancel':
                    go_flow_instance_obj.sync_order_cancel_filter = False
                elif state == 'need_to_review':
                    go_flow_instance_obj.sync_order_review_filter = False

    def _sale_write_status(self, orders, state):
        if state == 'cancel':
            go_flow_order_ids = [order.get('id', '') for order in orders if order.get('status') == 'canceled']
        else:
            # check and separate oh_hold orders and need_to_review orders
            go_flow_order_ids = []
            need_to_review_order_ids = []
            on_hold_order_ids = []
            for order in orders:
                order_id = order.get('id', '')
                go_flow_order_ids.append(order_id)
                status = order.get('status')
                if status == 'on_hold':
                    on_hold_order_ids.append(order_id)
                elif status == 'need_to_review':
                    need_to_review_order_ids.append(order_id)

        if go_flow_order_ids:
            goflow_order_ids_brw = self.env['goflow.order'].search([('goflow_order_id', 'in', go_flow_order_ids)])
            if state == 'cancel':
                self.order_to_cancel(goflow_order_ids_brw)
                goflow_order_ids_brw.sudo().write({'goflow_order_status': str(state)})
                goflow_order_ids_brw.sudo().sale_order_id.write({'goflow_order_status': 'canceled'})
                # need_to_review_order_ids.sale_order_id.sudo().action_cancel()
            elif state == 'need_to_review':
                to_on_hold = goflow_order_ids_brw.filtered(lambda l: l.goflow_order_id in on_hold_order_ids)
                to_review = goflow_order_ids_brw.filtered(lambda l: l.goflow_order_id in need_to_review_order_ids)
                if to_review:
                    to_review.sudo().write({'goflow_order_status': 'need_to_review'})
                    to_review.sale_order_id.sudo().write({'state': 'need_to_review',
                                                          'goflow_order_status': 'need_to_review'
                                                          })
                if to_on_hold:
                    to_on_hold.sudo().write({'goflow_order_status': 'on_hold'})
                    to_on_hold.sale_order_id.sudo().write({'state': 'hold',
                                                           'goflow_order_status': 'on_hold'
                                                           })

    def _get_date_filter(self, go_flow_instance_obj, filter_date):
        sync_date = go_flow_instance_obj.convert_odoo_date_to_goflow_format(filter_date)
        dt_format = '%Y-%m-%dT%H:%M:%S.%fZ' if len(sync_date) >= 21 else '%Y-%m-%dT%H:%M:%SZ'
        dt_object = datetime.strptime(sync_date, dt_format)
        zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
        zero_time_str = zero_time.strftime(dt_format)
        return zero_time_str

    def order_to_cancel(self, need_to_review_order_ids):
        so_ids = need_to_review_order_ids.sudo().sale_order_id.filtered(lambda s: s.state != 'cancel')
        done_so_ids = so_ids.filtered(lambda s: 'done' in s.picking_ids.mapped('state'))
        direct_cancel = so_ids - done_so_ids
        if direct_cancel:
            direct_cancel.with_context(disable_cancel_warning=True, cancelled_from_goflow=True, salewizard=True).action_cancel()
        if done_so_ids:
            for sale_to_cancel in done_so_ids:
                if not sale_to_cancel.picking_ids.filtered(lambda p: p.state == 'done' and (p.picking_type_code == 'outgoing'
                      or p.picking_type_code == 'incoming')):
                    self.return_done_pickings(sale_to_cancel)
                    sale_to_cancel.with_context(disable_cancel_warning=True, cancelled_from_goflow=True, salewizard=True).action_cancel()

    def return_done_pickings(self, sale_to_cancel):
        pickings_to_return = sale_to_cancel.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_code != 'outgoing'
                      and p.picking_type_code != 'incoming').sorted('id', reverse=True)
        for return_pick in pickings_to_return:
            # Create a return of done picking
            return_picking_wizard_id = self.env['stock.return.picking'].with_context(active_id=return_pick.id,
                                                                                     active_ids=return_pick.ids,
                                                                                     active_model='stock.picking').create(
                {})
            for line in return_picking_wizard_id.product_return_moves:
                if not line.quantity:
                    line.quantity = line.move_id.quantity_done
            action = return_picking_wizard_id.create_returns()
            if action.get('res_id', False):
                new_return_picking_id = self.env['stock.picking'].sudo().browse(action['res_id'])
                # for return_move in new_return_picking_id.move_ids:
                #     return_move.quantity_done = return_move.product_uom_qty
                new_return_picking_id.action_set_quantities_to_reservation()
                new_return_picking_id.button_validate()

    # passing carrier info to pickings
    # def action_confirm(self):
    #     res = super(SaleOrder, self).action_confirm()
    #     for order in self:
    #         if order.external_origin == 'manual' or not order.external_origin:
    #             pickings = order.picking_ids.filtered(
    #                 lambda rec: rec.state not in ('done', 'cancel'))
    #             picking_vals = {
    #                 'carrier_id': self.carrier_id if self.carrier_id else False,
    #                 'shipping_account': self.shipping_account if self.shipping_account else "",
    #             }
    #             pickings.write(picking_vals)
    #     return res

    def goflow_get_order_shipping_label_urls(self, pack_box=True):

        if self.external_origin == 'go_flow':
            # pack box API
            # if pack_box and not self.goflow_box_created:
            #     self.goflow_pack_box(self.move_line_ids_without_package)

            go_flow_instance_obj = self.env['goflow.configuration'].search(
                [('active', '=', True), ('state', '=', 'done')],
                limit=1)
            goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', self.sudo().warehouse_id.id)],
                                                                   limit=1)
            goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', self.id)], limit=1)
            url = f"/v1/orders/{goflow_order.goflow_order_id}/documents"
            if go_flow_instance_obj and goflow_warehouse.goflow_get_document and goflow_order:
                response = go_flow_instance_obj._send_goflow_request('get', url)
                if response.status_code == 200:
                    response = response.json()
                    data = response
                    attachments_list = []

                    if data.get('shipping_labels'):
                        shipping_label_url = data['shipping_labels']['all']['url']
                        shipping_label_datas = base64.b64encode(requests.get(shipping_label_url).content)

                        # zpl_file_path = "/home/ankhilesh.singh/Documents/python/shipping-label-for-order-2008977.zpl"
                        # with open(zpl_file_path, 'r') as zpl_file:
                        #     zpl_content = zpl_file.read()

                        zpl = requests.get(shipping_label_url).content

                        # adjust print density (8dpmm), label width (4 inches), label height (6 inches), and label index (0) as necessary
                        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/4x6/'
                        files = {'file': zpl}
                        headers = {'Accept': 'application/pdf',
                                   'X-Rotation': '180'}  # omit this line to get PNG images back
                        response = requests.post(url, headers=headers, files=files, stream=True)

                        if response.status_code == 200:
                            response.raw.decode_content = True
                            b64encoded_str = base64.b64encode(response.content)
                            shipping_labels = self.env["ir.attachment"].create({
                                'name': 'Shipping Labels All',
                                'datas': b64encoded_str,
                                'type': 'binary',
                                'url': shipping_label_url,
                            })
                            if shipping_labels:
                                attachments_list.append(shipping_labels.id)
                        else:
                            self.message_post(body="Shipping Label Documents Response Failed")

                    if attachments_list:
                        self.message_post(body="Shipping Label Documents Successfully Fetch",
                                          attachment_ids=attachments_list)
                    else:
                        self.message_post(body="No Shipping Label Document Found. Please try again")
                else:
                    response = json.loads(response.text)
                    raise ValidationError(
                        "Get Documents failed due to this reason: %s, Please check this with IT team" % response)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    goflow_order_line_id = fields.Char()



class ResCompany(models.Model):
    _inherit = 'res.company'

    goflow_customer_ids = fields.Many2many('res.partner',string='Goflow Customers')
    goflow_mail_user_ids = fields.Many2many('res.users','res_company_goflow_mail_user_ids',string='Goflow Fail Mail Users')
    goflow_store_ids = fields.Many2many('goflow.store','goflow_store_ids',string='Goflow Stores')
    goflow_review_order_ids = fields.Many2many('goflow.store','goflow_review_order_ids',string='Goflow Review Order Stores')
    goflow_ship = fields.Boolean('')
    goflow_api_user = fields.Many2one('res.users')



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    goflow_customer_ids = fields.Many2many('res.partner', related='company_id.goflow_customer_ids',
        string='Customers', readonly=False)
    
    goflow_mail_user_ids = fields.Many2many('res.users', related='company_id.goflow_mail_user_ids',
        string='Goflow Fail Mail Users', readonly=False)

    shipping_product = fields.Many2one('product.product', 'Shipping Product', domain="[('type', '=', 'service')]",config_parameter='bista_go_flow.shipping_product', )
    discount_product = fields.Many2one('product.product', 'Discount Product', domain="[('type', '=', 'service')]",config_parameter='bista_go_flow.discount_product', )



class ResUsers(models.Model):
    _inherit = 'res.users'

    location = fields.Char()

