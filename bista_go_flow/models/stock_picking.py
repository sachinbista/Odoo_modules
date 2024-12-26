# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import json
import random

import requests
import base64
import io
import zipfile
import os

import shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    picking_type_code = fields.Selection(related='picking_type_id.code', store=True)
    sign_template_id = fields.Many2one('sign.template', string='Sign Document')

    goflow_routing_status = fields.Selection([
        ("shipping_requested", "Shipping Requested"),
        ("ready_to_receive", "Ready to Receive"),
        ("routing_requested", "Routing Requested"),
        ("routing_received", "Routing Received"),
        ("doc_generated", "Document Generated"),
        ("require_manual_shipment", "Require Manual Shipment"),
    ], string="Shipping Status", copy=False, track_visibility='always')

    goflow_routing_req_by = fields.Many2one('res.users', 'Goflow Routing Requested by', copy=False)
    goflow_routing_req_date = fields.Datetime('Goflow Routing Requested Date', copy=False)

    goflow_hold_reason = fields.Text("", compute="_compute_go_flow_hold_reasons", copy=False)
    goflow_store_id = fields.Many2one(related="sale_id.goflow_store_id", store=True, copy=False)

    identify_pack_picking = fields.Boolean(compute='_compute_identify_pack_picking', copy=False)

    external_origin = fields.Selection([
        ('manual', 'Manual'),
        ('go_flow', 'Go Flow'),
        ('spring_system', 'Spring System'),
        ('market_time', 'Market Time')], string='Order From', default='manual', readonly=True, store=True, copy=False)
    goflow_customer_name = fields.Char("", copy=False)
    goflow_street1 = fields.Char("", copy=False)
    goflow_street2 = fields.Char("", copy=False)
    goflow_city = fields.Char("", copy=False)
    goflow_state = fields.Char("", copy=False)
    goflow_zip_code = fields.Char("", copy=False)
    goflow_country_code = fields.Char("", copy=False)

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
    goflow_routing_request_enable = fields.Boolean()
    shipping_account = fields.Char()
    sale_state = fields.Selection(related="sale_id.state")
    total_weight = fields.Float("Total Weight", readonly=True)
    total_length = fields.Float("Total Length", readonly=True)
    total_width = fields.Float("Total Width", readonly=True)
    total_height = fields.Float("Total Height", readonly=True)
    rpa_process_priority = fields.Integer(string="RPA Priority", store=True)
    goflow_order_id = fields.Char(string="Goflow Order ID")
    rpa_status = fields.Boolean(string="Automatic RPA Process")
    goflow_document = fields.Binary(string="Zip File",
                                    help="Used to Upload all shipping related  documents in zip formate please upload only zip file format")
    goflow_document_filename = fields.Char(string="Shipping Document")
    extracted_shipping_files = fields.One2many('shipping.documents', 'picking_id', string='Shipping Documents')
    delivery_shipping_files = fields.One2many('shipping.documents', 'delivery_picking_id', string='Delivery Documents')
    shipping_request = fields.Boolean(related="picking_type_id.api_shipping_request")
    goflow_order_no = fields.Char(string="Goflow Order No.")
    manual_overwridden = fields.Boolean(string="Manual Overwride.")
    rpa_process_type = fields.Selection([
        ("all", "Pack All"),
        ("is_separate_box", "Is Separate Box"),
        ("individual_separate_multi_box", "Individual Separate Multi Box"),
        ("individual_item_same_box", "Individual Item Same Box"),
        ("split_multi_box", "Split Multi Box"),
        ("mixed", "Mixed")], copy=False, string="RPA Process Type")
    proceed_wrong_warehouse = fields.Boolean()


    def _create_backorder(self):
        backorders = super(StockPicking, self)._create_backorder()
        backorders.external_origin = backorders.backorder_id.external_origin
        return backorders


    def write(self, vals):
        result = super(StockPicking, self).write(vals)
        if 'goflow_document' in vals and vals['goflow_document']:
            self.extracted_shipping_files.unlink()
            # attachments_str = []
            # Check if the uploaded file is a valid zip file
            try:
                zip_content = base64.b64decode(vals['goflow_document'])
                zip_file = io.BytesIO(zip_content)
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    for file_name in zip_ref.namelist():
                        # Read the content of each file
                        file_content = zip_ref.read(file_name)
                        # Use a single line to get move_dest_ids and picking_ids
                        next_picking_id = self.move_ids.mapped('move_dest_ids.picking_id')[
                            0] if self.move_ids and self.move_ids.mapped('move_dest_ids.picking_id') else self
                        # Create a record in the extracted files model
                        extracted_file = self.env['shipping.documents'].create({
                            'picking_id': self.id,
                            'delivery_picking_id': next_picking_id.id if next_picking_id  else False,
                            'shipping_file_name': file_name,
                            'file_content': base64.b64encode(file_content),
                            'call_auto_print': True
                        })
                        # attachments_str.append(file_name)

                    self.goflow_routing_status = 'doc_generated'
                    # if attachments_str:
                    #     # Post a message in the chatter
                    #     attachments_html = '<br/>'.join(attachments_str)
                    #     self.message_post(body=f"Following Documents Successfully Fetch:<br/>{attachments_html}")
                    #
                    # if attachments_str and len(attachments_str) >= 1:
                    #     self.goflow_routing_status = 'doc_generated'


            except zipfile.BadZipFile:
                # Raise a user warning if the uploaded file is not a valid zip
                raise ValidationError(
                    "The uploaded file is not a valid zip file, please upload a zipfile.")
                # raise UserError(_("The uploaded file is not a valid zip file, please upload a valid zipfile."))

        if 'goflow_routing_status' in vals and vals['goflow_routing_status'] in ('shipping_requested', 'doc_generated'):
            self.goflow_document = False

        return result

    @api.onchange('total_pallet_count','move_line_ids_without_package','total_quantities')
    def _set_rpa_process_type(self):
        # print("_set_rpa_process_type:::::::::::::::")
        # pack box process checking
        if self.external_origin == 'go_flow':
            # case - all
            package_ids = list(set(self.move_line_ids_without_package.mapped('result_package_id')))
            if len(package_ids) == 1 and len(self.move_line_ids_without_package) == len(self.move_ids_without_package):
                self.move_line_ids_without_package.filtered(lambda l: l.result_package_id).update({'rpa_process_type':'all'})
                self.rpa_process_type = 'all'

            # case - is_separate_box
            product_id_list = []
            for move_line in self.move_line_ids_without_package:
                if move_line.product_id.id not in product_id_list:
                    product_id_list.append(move_line.product_id.id)
                elif move_line.product_id.id in product_id_list and move_line.qty_done == 1:
                    move_line.rpa_process_type = 'is_separate_box'

            # case - is_separate_box for newly created record
            if len(self.move_line_ids_without_package) > len(self.move_ids_without_package):
                separate_box_rec = self.move_line_ids_without_package.filtered(lambda l: l.rpa_process_type == 'is_separate_box')
                if len(separate_box_rec) > 1:
                    for sep in separate_box_rec:
                        rec = self.move_line_ids_without_package.filtered(lambda l: l.move_id.id == sep.move_id.id)
                        if rec:
                            rec.rpa_process_type = 'is_separate_box'
                else:
                    rec = self.move_line_ids_without_package.filtered(lambda l: l.move_id.id == separate_box_rec.move_id.id)
                    if rec:
                        rec.rpa_process_type = 'is_separate_box'
                for mline in self.move_line_ids_without_package.filtered(lambda l: not l.result_package_id):
                    mline.rpa_process_type = ''


            # case - individual_item_same_box
            package_ids = self.move_line_ids_without_package.filtered(lambda l: not l.rpa_process_type or l.rpa_process_type == 'all').mapped('result_package_id')
            product_ids = self.move_line_ids_without_package.mapped('product_id')
            rec = self.move_line_ids_without_package.filtered(lambda l: l.result_package_id.id in package_ids.ids)
            if len(package_ids) == 1 and len(rec.mapped('product_id')) > 1 and rec.filtered(lambda s: not s.rpa_process_type):
                rec.rpa_process_type = 'individual_item_same_box'


            # case - split_multi_box
            if self.carrier_id:
                for move_line in self.move_line_ids_without_package:
                    if move_line.result_package_id:
                        rec = self.move_line_ids_without_package.filtered(lambda l: l.result_package_id and l.result_package_id.package_type_id.id == move_line.result_package_id.package_type_id.id)

                        product_list = rec.mapped('product_id')
                        if len(rec) > 1 and len(product_list) == 1:
                            rec.rpa_process_type = 'split_multi_box'

            # case - individual_separate_multi_box
            move_id_list = []
            for move_line in self.move_line_ids_without_package:
                if move_line.rpa_process_type not in ['is_separate_box','individual_item_same_box','split_multi_box']:
                    if move_line.move_id.id not in move_id_list:
                        move_id_list.append(move_line.move_id.id)
                    elif move_line.move_id.id in move_id_list:
                        move_line.rpa_process_type = 'individual_separate_multi_box'

            # case - mixed
            rpa_process_type = self.move_line_ids_without_package.filtered(lambda m: m.rpa_process_type).mapped('rpa_process_type')
            same_rpa_process_type = len(set(rpa_process_type)) == 1
            if not same_rpa_process_type:
                self.rpa_process_type = 'mixed'
            else:
                self.rpa_process_type = self.move_line_ids_without_package[0].rpa_process_type
        

    def _put_in_pack(self, move_line_ids, create_package_level=True):
        res = super(StockPicking, self)._put_in_pack(move_line_ids, create_package_level)

        if self.external_origin == 'go_flow':
            self._set_rpa_process_type()
        return res

    # @api.depends('move_ids_without_package')
    # def _compute_all_weights(self):
    #     for rec in self:
    #         moves_without_package = rec.move_ids_without_package
    #         rec.total_weight = sum(moves_without_package.mapped('product_id.weight'))
    #         rec.total_length = sum(moves_without_package.mapped('product_id.product_length'))
    #         rec.total_width = sum(moves_without_package.mapped('product_id.product_width'))
    #         rec.total_height = sum(moves_without_package.mapped('product_id.product_height'))

    def req_shipping(self):
        if self.external_origin == 'go_flow':
            sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

            go_flow_instance_obj = self.env['goflow.configuration'].search(
                [('active', '=', True), ('state', '=', 'done')], limit=1)
            if go_flow_instance_obj:
                goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)

                url = f"/v1/orders?filters[id]={goflow_order.goflow_order_id}"
                goflow_order_response = go_flow_instance_obj._send_goflow_request('get', url)
                if goflow_order_response:
                    goflow_order_response = goflow_order_response.json()
                    if goflow_order_response.get("data", []):
                        order = goflow_order_response.get("data", [])[0]

                        if order['status'] == 'canceled' and not self.manual_overwridden:
                            raise Warning(
                                'This order is cancelled in GoFlow. Please use manual orverwridden True to proceed further!!')
                        elif order['status'] != 'ready_to_pick':
                            self.update({'goflow_routing_status': 'require_manual_shipment'})
                            return True

            if self.goflow_store_id.require_manual_shipment or self.goflow_shipment_type in ['ltl', 'pickup']:
                self.goflow_routing_status = 'require_manual_shipment'
            elif self.total_pallet_count == 1 or self.total_pallet_count == 0:
                self.goflow_routing_status = 'shipping_requested'
            else:
                self.update({'goflow_routing_status': 'require_manual_shipment'})

    def goflow_get_documents(self):
        stock_picking = self.env['stock.picking'].search([('goflow_routing_status', '=', 'ready_to_receive')])
        for picking in stock_picking:
            picking.goflow_get_order_document_urls()

    # def action_put_in_pack(self):
    #     res = super().action_put_in_pack()
    #     self.update({'goflow_routing_status': 'packing_ready'})
    #     return res

    def _compute_identify_pack_picking(self):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        for rec in self:
            rec.identify_pack_picking = False
            if go_flow_instance_obj:
                sale_id = rec.sale_id if rec.sale_id else rec.sudo().intercom_sale_order_id
                # if (rec.move_ids_without_package and rec.move_ids_without_package[0].move_orig_ids and
                #         rec.move_ids_without_package[0].move_dest_ids and sale_id):
                if self.picking_type_id.api_shipping_request and sale_id:
                    # goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
                    # if goflow_order:
                    rec.identify_pack_picking = True

    @api.depends('origin')
    def _compute_go_flow_hold_reasons(self):
        for rec in self:
            sale_orders = self.env['sale.order'].search([('name', '=', rec.origin)])
            hold_reasons = [str(order.goflow_hold_reason) for order in sale_orders if order.goflow_hold_reason]
            rec.goflow_hold_reason = '\n'.join(hold_reasons) or False

    def goflow_pack_box(self, move_lines):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        goflow_order_id = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
        goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', self.sudo().warehouse_id.id)],
                                                               limit=1)

        if go_flow_instance_obj and goflow_warehouse.goflow_sync_shipment:
            data = {}
            cnt = 0
            for line in move_lines:
                goflow_order_line_id = sale_id.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)
                if len(goflow_order_line_id) > 1:
                    goflow_order_line_id = goflow_order_line_id[0].goflow_order_line_id
                else:
                    goflow_order_line_id = sale_id.order_line.filtered(
                        lambda x: x.product_id.id == line.product_id.id).goflow_order_line_id
                cnt = cnt + 1

                if not line.qty_done:
                    raise ValidationError("Please add enough Quantity!")
                data = self._prepare_pack_box_data(cnt, line, goflow_order_id, goflow_order_line_id,
                                                   line.qty_done)

                if goflow_order_id and goflow_order_line_id:
                    url = f"/v1/orders/{goflow_order_id.goflow_order_id}/shipment/boxes"
                    response = go_flow_instance_obj._send_goflow_request('post', url, payload=data)

                    if response.status_code == 200:
                        response = response.json()
                        line.goflow_box_id = response.get('box_id')
                        self.goflow_box_created = True
                        self.message_post(body='Box created successfully for %s' % line.product_id.name)
                    else:
                        response = json.loads(response.text)
                        raise ValidationError(
                            "Box is not generated due to this reason: %s, Please check this with IT team" % response)

    def _prepare_pack_box_data(self, count, line, goflow_order_id, goflow_order_line_id, qty):
        weight_amt = line.product_id.weight * qty
        box_length = line.product_id.product_length
        box_width = line.product_id.product_width
        box_height = line.product_id.product_height
        if line.result_package_id:
            if line.result_package_id.package_type_id:
                if line.result_package_id.package_type_id.base_weight:
                    weight_amt = line.result_package_id.package_type_id.base_weight
                if line.result_package_id.package_type_id.packaging_length and line.result_package_id.package_type_id.width and line.result_package_id.package_type_id.height:
                    box_length = line.result_package_id.package_type_id.packaging_length
                    box_width = line.result_package_id.package_type_id.width
                    box_height = line.result_package_id.package_type_id.height

        tracking_number = ""  # str(goflow_order_id.order_number) + "-" + str(count)
        if self.carrier_tracking_ref:
            tracking_number = self.carrier_tracking_ref
        data = {
            "cost": {
                "amount": float(line.product_id.standard_price or 0.0)
            },
            "tracking_number": str(tracking_number),
            "sscc": "",  # 20 digit str str(random.randint(10000000000000000000,99999999999999999999))
            "weight": {
                "measure": "pounds",
                "amount": float(weight_amt or 0.0)
            },
            "dimensions": {
                "measure": "inches",
                "length": float(box_length or 0.0),
                "width": float(box_width or 0.0),
                "height": float(box_height or 0.0)
            },
            "lines": [{
                "order_line_id": str(goflow_order_line_id),
                "quantity": int(qty or 0)
            }]
        }
        return data

    def goflow_unpack_box(self, move_lines):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        goflow_order_id = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
        if go_flow_instance_obj:
            for line in move_lines:
                if goflow_order_id and line.goflow_box_id:
                    url = f"/v1/orders/{goflow_order_id.goflow_order_id}/shipment/boxes/{line.goflow_box_id}"
                    response = go_flow_instance_obj._send_goflow_request('delete', url)
                    if response.status_code == 204:
                        response = response.status_code
                    else:
                        response = json.loads(response.text)

    def goflow_edit_box(self, move_lines):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
        if go_flow_instance_obj:
            data = {}
            cnt = 0
            tracking_number = ""  # str(goflow_order.order_number) + "-" + str(cnt)
            if self.carrier_tracking_ref:
                tracking_number = self.carrier_tracking_ref
            for line in move_lines:
                cnt = cnt + 1
                data = {
                    "tracking_number": str(tracking_number),
                }
                if goflow_order and line.goflow_box_id:
                    url = f"/v1/orders/{goflow_order.goflow_order_id}/shipment/boxes/{line.goflow_box_id}"
                    response = go_flow_instance_obj._send_goflow_request('patch', url, payload=data)
                    if response.status_code == 204:
                        self.message_post(body='Tracking Number set successfully for %s' % line.product_id.name)
                    else:
                        response = json.loads(response.text)

    def goflow_shipment_ready(self):
        self.goflow_pack_box(self.move_line_ids_without_package)

    def goflow_shipment_edit(self):
        self.goflow_edit_box(self.move_line_ids_without_package)

    def goflow_send_request_routing(self):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id
        self.go_flow_request_routing()

    # post request routing
    def go_flow_request_routing(self):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

        # pack box
        if not self.goflow_box_created:
            self.goflow_pack_box(self.move_line_ids_without_package)

        total_product_qty = sum(self.move_ids_without_package.mapped('product_uom_qty'))
        product_qty = sum(self.move_ids_without_package.mapped('quantity_done'))
        if product_qty < total_product_qty:
            raise ValidationError("Please add enough Quantity!")
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)])
        if go_flow_instance_obj and goflow_order:
            url = f"/v1/orders/{goflow_order.goflow_order_id}/shipment-routing-request"

            data = self._prepare_routing_request_data(go_flow_instance_obj)

            response = go_flow_instance_obj._send_goflow_request('post', url, payload=data)
            if response.status_code == 200:
                self.goflow_routing_status = "routing_requested"
                self.goflow_routing_req_by = self.env.user.id
                self.goflow_routing_req_date = datetime.now()
            else:
                response = response.json()
                raise ValidationError(
                    "Routing request failed due to this reason: %s, Please check this with IT team" % response.get(
                        'message'))

    def _prepare_routing_request_data(self, go_flow_instance_obj):
        # print("_prepare_routing_request_data::::::::::::::::::::::::")
        box_count = self.total_pallet_count
        pallet_count = self.total_pallet_count
        cubic_volume = 0.0
        # ready_for_pickup_at = go_flow_instance_obj.convert_odoo_date_to_goflow_format(self.scheduled_date)
        data = {
            "weight": {
                "measure": "pounds",
                "amount": float(self.shipping_weight) or 0.0
            },
            "boxes": {
                "count": int(box_count) or 0
            },
            "pallets": {
                "count": int(pallet_count) or 0,
                "is_stackable": True
            },
            # "cubic_volume": {
            #     "measure": "feet",
            #     "amount": float(cubic_volume) or 0.0
            # },
            # "freight_class": "",
            # "ready_for_pickup_at": ""
        }
        return data

    # def goflow_fetch_routing_request(self):
    #     sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id
    #     sale_id.go_flow_fetch_shipment_routing_request()
    #     self.goflow_routing_status = "routing_received"

    def goflow_submit_order_shipments(self):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
        goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', self.sudo().warehouse_id.id)],
                                                               limit=1)
        if go_flow_instance_obj and goflow_warehouse.goflow_sync_shipment:
            notify_store = False
            if sale_id.sudo().goflow_shipment_type not in ['pickup', 'messenger']:
                notify_store = True
            else:
                notify_store = False

            data = {
                "requests": [
                    {
                        "order_id": int(goflow_order.goflow_order_id),
                        "notify_store": notify_store,
                        "shipment_type": str(
                            sale_id.sudo().goflow_shipment_type) if sale_id.sudo().goflow_shipment_type else "",
                        "carrier": str(sale_id.sudo().goflow_carrier) if sale_id.sudo().goflow_carrier else None,
                        "shipping_method": str(
                            sale_id.sudo().goflow_shipping_method) if sale_id.sudo().goflow_shipping_method else None,
                        "scac": str(sale_id.sudo().goflow_scac) if sale_id.sudo().goflow_scac else None,
                        "currency_code": str(
                            sale_id.sudo().goflow_currency_code) if sale_id.sudo().goflow_currency_code else None,
                    }
                ]
            }
            if goflow_order and data:
                response = go_flow_instance_obj._send_goflow_request('post', '/v1/orders/shipments/feeds', payload=data)
                if response.status_code == 202:
                    response = json.loads(response.text)
                    self.goflow_fetch_feed_response(response)
                else:
                    response = json.loads(response.text)
                    self.goflow_fetch_feed_response(response)

    def goflow_fetch_feed_response(self, data):
        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        url = f"/v1/orders/shipments/feeds/{data['id']}"
        if go_flow_instance_obj and data:
            response = go_flow_instance_obj._send_goflow_request('get', url)
            response = json.loads(response.text)
            if response:
                if response.get('responses'):
                    if response['responses'][0]['error'] == None:
                        self.message_post(body="Goflow Order is Shipped")
                    else:
                        self.message_post(body=response['responses'][0]['error'])

    def goflow_get_order_document_urls(self, pack_box=True):

        if self.external_origin == 'manual':
            if not self.carrier_id:
                raise ValidationError("Please set carrier to proceed.")
            self.send_to_shipper()
            if self.carrier_tracking_ref:
                self.goflow_routing_status = 'doc_generated'
        elif self.external_origin == 'go_flow':
            # pack box API
            # if pack_box and not self.goflow_box_created:
            #     self.goflow_pack_box(self.move_line_ids_without_package)

            sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

            go_flow_instance_obj = self.env['goflow.configuration'].search(
                [('active', '=', True), ('state', '=', 'done')],
                limit=1)
            goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', self.sudo().warehouse_id.id)],
                                                                   limit=1)
            goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
            url = f"/v1/orders/{goflow_order.goflow_order_id}/documents"
            if go_flow_instance_obj and goflow_warehouse.goflow_get_document and goflow_order:
                response = go_flow_instance_obj._send_goflow_request('get', url)
                if response.status_code == 200:
                    response = response.json()
                    data = response
                    attachments_list = []

                    # packing_slips
                    packing_slips = data['packing_slips']
                    cnt = 0
                    slips_datas = False
                    for slips in packing_slips:
                        cnt += 1
                        slips_datas = base64.b64encode(requests.get(slips['url']).content)

                        slips_attach = self.env["ir.attachment"].create({
                            'name': 'Packing Slips - ' + str(cnt),
                            'datas': slips_datas,
                            'type': 'binary',
                            'url': slips['url'],
                        })
                        if slips_attach:
                            attachments_list.append(slips_attach.id)

                    # bill_of_lading
                    bill_of_lading = False
                    if data.get('bill_of_lading'):
                        bill_of_lading_url = data['bill_of_lading']['url']
                        bill_of_lading_datas = base64.b64encode(requests.get(bill_of_lading_url).content)

                        bill_of_lading = self.env["ir.attachment"].create({
                            'name': 'Bill of Lading',
                            'datas': bill_of_lading_datas,
                            'type': 'binary',
                            'url': bill_of_lading_url,
                        })
                        self.sign_template_id = self.env['sign.template'].create({
                            'attachment_id': bill_of_lading.id,
                            'sign_item_ids': [
                                Command.create({'type_id': self.env.ref('sign.sign_item_type_signature').id,
                                                'responsible_id': self.env.ref(
                                                    'sign.sign_item_role_customer').id, 'required': True, 'page': 1,
                                                'posX': 0.707, 'posY': 0.745, 'height': 0.050,
                                                'width': 0.200}),
                                Command.create({
                                    'type_id': self.env.ref('sign.sign_item_type_text').id,
                                    'responsible_id': self.env.ref(
                                        'sign.sign_item_role_customer').id,
                                    'required': False,
                                    'page': 1,
                                    'posX': 0.800,
                                    'posY': 0.173,
                                    'width': 0.150,
                                    'height': 0.015,
                                })

                            ]})
                        sign_request = self.env['sign.send.request'].create({
                            'template_id': self.sign_template_id.id,
                            'signer_id': self.env.user.partner_id.id,
                            'filename': "Bill of Lading",
                            # 'picking_id':self.picking_id,
                            'subject': _("Signature Request - %(file_name)s",
                                         file_name=self.sign_template_id.attachment_id.name),
                        }).with_context({'template_id': self.sign_template_id, 'default_role_id': 1,
                                         'picking_id': self.id}).create_request()
                    # request.go_to_signable_document(request.request_item_ids)
                    # self.env['bus.bus']._sendone('broadcast', 'web.notify', {

                    # })
                    # carton_labels
                    carton_labels = False
                    if data.get('carton_labels'):
                        carton_labels_url = data['carton_labels']['all']['url']
                        carton_labels_datas = base64.b64encode(requests.get(carton_labels_url).content)

                        carton_labels = self.env["ir.attachment"].create({
                            'name': 'Carton Labels All',
                            'datas': carton_labels_datas,
                            'type': 'binary',
                            'url': carton_labels_url,
                        })
                    if bill_of_lading:
                        attachments_list.append(bill_of_lading.id)

                    if data.get('shipping_labels'):
                        shipping_label_url = data['shipping_labels']['all']['url']
                        shipping_label_datas = base64.b64encode(requests.get(shipping_label_url).content)

                        shipping_labels = self.env["ir.attachment"].create({
                            'name': 'Shipping Labels All',
                            'datas': shipping_label_datas,
                            'type': 'binary',
                            'url': shipping_label_url,
                        })
                        if shipping_labels:
                            attachments_list.append(shipping_labels.id)

                    if carton_labels:
                        attachments_list.append(carton_labels.id)
                    if attachments_list:
                        self.message_post(body="Documents Successfully Fetch", attachment_ids=attachments_list)
                        self.goflow_routing_status = 'doc_generated'
                    else:
                        self.message_post(body="No Document Found. Please try again")
                else:
                    response = json.loads(response.text)
                    raise ValidationError(
                        "Get Documents failed due to this reason: %s, Please check this with IT team" % response)

    def goflow_split_order(self, order_status):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')],
                                                                       limit=1)
        goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
        if go_flow_instance_obj:
            lines_validate = []
            lines_validate_with_product = []
            lines_not_validate = []
            for line in self.move_ids_without_package:
                goflow_order_line_id = sale_id.order_line.filtered(
                    lambda x: x.product_id.id == line.product_id.id).goflow_order_line_id
                sale_order_qty = sum(
                    sale_id.order_line.filtered(lambda x: x.product_id.id == line.product_id.id).mapped(
                        'product_uom_qty'))
                qty = sale_order_qty - line.quantity_done
                if goflow_order_line_id:
                    if line.quantity_done > 0:
                        lines_validate.append({
                            "id": str(goflow_order_line_id),
                            "quantity": int(line.quantity_done)
                        })
                        lines_validate_with_product.append({
                            "id": str(goflow_order_line_id),
                            "product": str(line.product_id.name),
                            "quantity": int(line.quantity_done)
                        })
                    if qty > 0:
                        lines_not_validate.append({
                            "id": str(goflow_order_line_id),
                            "quantity": int(qty)
                        })
            data = {}
            chunks = []
            if lines_validate and lines_not_validate:
                chunks.append({"lines": lines_validate})
                chunks.append({"lines": lines_not_validate})
                data = {
                    "chunks": chunks,
                }
            if goflow_order and data:
                url = f"/v1/orders/{goflow_order.goflow_order_id}/splits"
                response = go_flow_instance_obj._send_goflow_request('post', url, payload=data)
                if response.status_code == 200:
                    response = response.json()
                    self._create_goflow_new_split_order_in_odoo(goflow_order, lines_validate_with_product, response,
                                                                go_flow_instance_obj, order_status)
                else:
                    response = json.loads(response.text)

    def _create_goflow_new_split_order_in_odoo(self, goflow_order, lines_validate_with_product, response,
                                               go_flow_instance_obj, order_status):
        goflow_order_obj = self.env['goflow.order']
        orders = response.get("orders", [])
        order_found = False
        if orders:
            for order in orders:
                # check and change exist goflow_order id and order number
                match_order = 0
                found_order_id = 0
                if not order_found:
                    if order['lines']:
                        for line in order['lines']:
                            for val_line in lines_validate_with_product:
                                if line['product']['name'] == val_line['product']:
                                    if line['quantity']['amount'] == val_line['quantity']:
                                        match_order = order['id']
                                        curr_order = goflow_order_obj.search(
                                            [('goflow_order_id', '=', goflow_order.goflow_order_id)])
                                        curr_order.goflow_order_id = order['id']
                                        curr_order.order_number = order['order_number']
                                        # curr_order.order_data = order
                                        order_found = True
                                        found_order_id = order['id']

                if found_order_id != order['id']:
                    exist_order = goflow_order_obj.search([('goflow_order_id', '=', order['id'])])
                    if not exist_order:
                        goflow_order.create_goflow_order(order, go_flow_instance_obj)

                        # find new order
                        new_order = goflow_order_obj.search([('goflow_order_id', '=', order['id'])])
                        # call hold API
                        if order_status == 'hold':
                            new_order.goflow_set_order_hold()
                            if new_order.sale_order_id.state == 'hold':
                                self.sudo().message_post(body="New Goflow order Successfully set On Hold")
                        if order_status == 'cancel':
                            new_order.sale_order_id._action_cancel()
                            if new_order.sale_order_id.state == 'cancel':
                                self.sudo().message_post(body="New Goflow order Successfully Cancelled")

    # changes product qty of sale order if this order is goflow order
    def change_sale_order_qty(self, order_status):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id
        goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', self.sudo().warehouse_id.id)],
                                                               limit=1)
        if goflow_warehouse.goflow_sync_shipment:
            if not self.move_ids_without_package[0].move_orig_ids and self.move_ids_without_package[
                0].move_dest_ids and sale_id:
                goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
                if goflow_order:
                    # calling goflow split order API
                    self.goflow_split_order(order_status)
                    for sale_line in sale_id.order_line:
                        move_product_qty = sum(self.move_ids_without_package.filtered(
                            lambda x: x.product_id.id == sale_line.product_id.id).mapped('quantity_done'))
                        if sale_line.product_uom_qty != move_product_qty:
                            sale_line.product_uom_qty = move_product_qty

    def button_validate(self):
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id
        if sale_id and sale_id.sudo().state in ('hold', 'need_to_review'):
            raise ValidationError(_("Cannot validate order which is in Need to review or Hold state"))

        ### Check goflow order warehouse before validation to switch warehouse###
        if self.external_origin == 'go_flow':
            self.check_goflow_order_warehouse_to_switch(sale_id)


        res = super().button_validate()
        if self.company_id.goflow_ship:
            sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

            go_flow_instance_obj = self.env['goflow.configuration'].search(
                [('active', '=', True), ('state', '=', 'done')], limit=1)
            goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', sale_id.sudo().warehouse_id.id)],
                                                                   limit=1)
            if go_flow_instance_obj and goflow_warehouse.goflow_sync_shipment:
                # PACK picking
                if self.picking_type_id.api_shipping_request and sale_id and self.external_origin == 'go_flow':
                    if not self.goflow_routing_status:
                        raise ValidationError(
                            "There is some problem while processing this request. Either Routing is not requested or Document is not generated. Please check and try again !!")
                    elif self.goflow_routing_status == 'routing_requested':
                        raise ValidationError(
                            "There is some problem while processing this request. Routing is not received. Please check and try again !!")
                    elif self.goflow_routing_status == 'routing_received':
                        raise ValidationError(
                            "There is some problem while processing this request. Document is not generated. Please check and try again !!")

                    # self.goflow_pack_box(self.move_line_ids_without_package)
        if sale_id and self.picking_type_id.code == "outgoing" and self.external_origin == 'go_flow':
            sale_id.goflow_get_order_shipping_label_urls()

                # delivery picking
                # if sale_id and self.picking_type_id.code == "outgoing" and self.external_origin == 'go_flow':
                #     goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
                #     if goflow_order:
                #         self.goflow_submit_order_shipments()
        return res

    def _action_generate_backorder_wizard(self, show_transfers=False):
        # identify goflow split order
        identify_goflow_split_order = False
        sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id
        goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', sale_id.sudo().warehouse_id.id)],
                                                               limit=1)

        if goflow_warehouse.goflow_sync_shipment:
            if not self.move_ids_without_package[0].move_orig_ids and self.move_ids_without_package[
                0].move_dest_ids and sale_id:
                goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
                if goflow_order:
                    identify_goflow_split_order = True

        view = self.env.ref('stock.view_backorder_confirmation')
        return {
            'name': _('Create Backorder?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.backorder.confirmation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_show_transfers=show_transfers,
                            default_pick_ids=[(4, p.id) for p in self],
                            default_identify_goflow_split_order=identify_goflow_split_order),
        }

    def action_bol_sign_document(self):
        if not self.sign_template_id:
            raise UserError("No sign template selected. Please select a sign template before signing.")
        request_id = self.env['sign.request'].search([('template_id', '=', self.sign_template_id.id)], limit=1)
        view = self.env.ref('bista_go_flow.sign_request_view_tree_inherit')
        action = self.env["ir.actions.actions"]._for_xml_id("bista_go_flow.sign_send_request_custom")
        action.update({
            'res_id': request_id.id,
            'target': 'current',
            'domain': [('id', '=', request_id.id)]
        })
        return action

    def check_n_reset_routing_status(self):
        today = datetime.now()
        NUMBER_OF_SECONDS = 172800
        if self.goflow_routing_req_date:
            if (today - self.goflow_routing_req_date).total_seconds() > NUMBER_OF_SECONDS:
                self.goflow_routing_status = ''
                self.goflow_routing_req_by = False
                self.goflow_routing_req_date = False

    @api.onchange("goflow_carrier")
    def _update_goflow_carrier_id(self):
        for rec in self:
            if rec.goflow_carrier:
                delivery_carrier = self.env['delivery.carrier'].search([('carrier_code', '=', rec.goflow_carrier)])
                if delivery_carrier:
                    rec.carrier_id = delivery_carrier.id

    def goflow_get_shipping_labels(self):
        if self.external_origin == 'go_flow':
            sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id
            go_flow_instance_obj = self.env['goflow.configuration'].search([
                ('active', '=', True), ('state', '=', 'done')], limit=1)
            goflow_warehouse = self.env['goflow.warehouse'].search([
                ('warehouse_id', '=', self.sudo().warehouse_id.id)], limit=1)
            goflow_order = self.env['goflow.order'].search([
                ('sale_order_id', '=', sale_id.id)], limit=1)
            url = f"/v1/orders/{goflow_order.goflow_order_id}/documents"
            if go_flow_instance_obj and goflow_warehouse.goflow_get_document and goflow_order:
                response = go_flow_instance_obj._send_goflow_request('get', url)
                documents_vals_lst = []
                document_file_names = []
                if response.status_code == 200:
                    response = response.json()
                    data = response
                    # shipping labels
                    if data.get('shipping_labels'):
                        shipping_label_url = data['shipping_labels']['all']['url']
                        zpl = requests.get(shipping_label_url).content
                        # adjust print density (8dpmm), label width (4 inches),
                        # label height (6 inches), and label index (0) as necessary
                        url = 'http://api.labelary.com/v1/printers/8dpmm/labels/4x6/'
                        files = {'file': zpl}
                        headers = {'Accept': 'application/pdf',
                                   'X-Rotation': '180'}  # omit this line to get PNG images back
                        response = requests.post(url, headers=headers, files=files, stream=True)
                        if response.status_code == 200:
                            response.raw.decode_content = True
                            shipping_label_pdf_datas = base64.b64encode(response.content)
                            shipping_label_filename = 'Shipping Labels All'
                            document_file_names.append(shipping_label_filename)
                            documents_vals_lst.append({
                                'picking_id': self.id,
                                'shipping_file_name': shipping_label_filename,
                                'file_content': shipping_label_pdf_datas,
                                'call_auto_print': True
                            })
                    # packing_slips
                    if data.get('packing_slips'):
                        cnt = 0
                        for slips in data.get('packing_slips'):
                            cnt += 1
                            slips_datas = base64.b64encode(requests.get(slips['url']).content)
                            slips_filename = 'Packing Slips - ' + str(cnt)
                            document_file_names.append(slips_filename)
                            documents_vals_lst.append({
                                'picking_id': self.id,
                                'shipping_file_name': slips_filename,
                                'file_content': slips_datas,
                                'call_auto_print': True
                            })
                    # bill_of_lading
                    if data.get('bill_of_lading'):
                        bill_of_lading_url = data['bill_of_lading']['url']
                        bill_of_lading_datas = base64.b64encode(requests.get(bill_of_lading_url).content)
                        bill_of_lading_filename = 'Bill of Lading'
                        document_file_names.append(bill_of_lading_filename)
                        documents_vals_lst.append({
                            'picking_id': self.id,
                            'shipping_file_name': bill_of_lading_filename,
                            'file_content': bill_of_lading_datas,
                            'call_auto_print': True
                        })
                    # carton_labels
                    if data.get('carton_labels'):
                        carton_labels_url = data['carton_labels']['all']['url']
                        carton_labels_datas = base64.b64encode(requests.get(carton_labels_url).content)
                        carton_labels_filename = 'Carton Labels All'
                        document_file_names.append(carton_labels_filename)
                        documents_vals_lst.append({
                            'picking_id': self.id,
                            'shipping_file_name': carton_labels_filename,
                            'file_content': carton_labels_datas,
                            'call_auto_print': True
                        })
                else:
                    response = json.loads(response.text)
                    raise ValidationError(
                        "Get Documents failed due to this reason: %s, Please check this with IT team" % response)
                if documents_vals_lst:
                    self.env['shipping.documents'].create(documents_vals_lst)
                    msg = '<br/>'.join(document_file_names)
                    self.message_post(body=f"Following Documents Successfully Fetched:<br/>{msg}")
                    self.goflow_routing_status = 'doc_generated'

    def goflow_get_order_shipping_label_urls(self, pack_box=True):

        if self.external_origin == 'go_flow':
            # pack box API
            # if pack_box and not self.goflow_box_created:
            #     self.goflow_pack_box(self.move_line_ids_without_package)

            sale_id = self.sale_id if self.sale_id else self.sudo().intercom_sale_order_id

            go_flow_instance_obj = self.env['goflow.configuration'].search(
                [('active', '=', True), ('state', '=', 'done')],
                limit=1)
            goflow_warehouse = self.env['goflow.warehouse'].search([('warehouse_id', '=', self.sudo().warehouse_id.id)],
                                                                   limit=1)
            goflow_order = self.env['goflow.order'].search([('sale_order_id', '=', sale_id.id)], limit=1)
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
    def check_goflow_order_warehouse_to_switch(self,sale_id):
        go_flow_instance = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done'), ('sale_order_import_operation', '=', True)])
        if go_flow_instance and sale_id.origin and not self.proceed_wrong_warehouse:
            url = '/v1/orders?filters[id]=' + str(sale_id.origin)
            goflow_order_response = go_flow_instance._send_goflow_request('get', url)
            if goflow_order_response:
                goflow_order_response = goflow_order_response.json()
                order = goflow_order_response.get("data", [])
                if order:
                    order = order[0]
                    goflow_store_id = self.env['goflow.store'].search([('store_id', '=', order['store']['id'])], limit=1)
                    if not goflow_store_id:
                        goflow_store_id = self._create_store(order['store'])

                    company_id = self.env['res.company'].sudo().search([('goflow_store_ids', 'in', goflow_store_id.id)],limit=1)
                    if not company_id:
                        company_id = self.env.ref('base.main_company')

                    goflow_warehouse = self.env['goflow.warehouse'].search([
                        ('goflow_warehouse_id', '=', order['warehouse']['id']),
                        ('company_id', '=', company_id.id)
                    ])
                    if goflow_warehouse:
                        if goflow_warehouse.warehouse_id.id != sale_id.warehouse_id.id:
                            raise ValidationError(_('This order initially created for warehouse <%s> but due to some reason warehouse changed to <%s> in GoFlow, To proceed further please use switch from warehouse feature' % (goflow_warehouse.warehouse_id.name,sale_id.warehouse_id.name)))
                            # ## Need to show wizard here to ask use to go for change warehouse or cancel##
                            # wizrd_action_id = self.env.ref('bista_go_flow.wiz_changed_warehouse_waring_action')
                            # msg = ("This order warehouse is changed in GoFlow from %s to %s " % (sale_id.warehouse_id.name, goflow_warehouse.goflow_warehouse_name))
                            #
                            # return {
                            #     'name': _("Change Warehouse Warning"),  # Name You want to display on wizard
                            #     'view_mode': 'form',
                            #     'view_id': wizrd_action_id,
                            #     'view_type': 'form',
                            #     'res_model': 'goflow.picking.validate.check',  # With . Example sale.order
                            #     'type': 'ir.actions.act_window',
                            #     'target': 'new',
                            # }


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    identify_goflow_split_order = fields.Boolean(copy=False)

    def split_hold_order(self):
        pickings_to_validate_ids = self.env.context.get('button_validate_picking_ids')
        if pickings_to_validate_ids:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate_ids)

            # calling goflow split order API
            if pickings_to_validate:
                pickings_to_validate.change_sale_order_qty(order_status='hold')

            self._check_less_quantities_than_expected(pickings_to_validate)
            return pickings_to_validate \
                .with_context(skip_backorder=True, picking_ids_not_to_backorder=self.pick_ids.ids) \
                .button_validate()
        return True

    def split_cancel_order(self):
        pickings_to_validate_ids = self.env.context.get('button_validate_picking_ids')
        if pickings_to_validate_ids:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate_ids)

            # calling goflow split order API
            if pickings_to_validate:
                pickings_to_validate.change_sale_order_qty(order_status='cancel')

            self._check_less_quantities_than_expected(pickings_to_validate)
            return pickings_to_validate \
                .with_context(skip_backorder=True, picking_ids_not_to_backorder=self.pick_ids.ids) \
                .button_validate()


class StockMove(models.Model):
    _inherit = 'stock.move'

    goflow_store_id = fields.Many2one(related="picking_id.goflow_store_id", store=True, copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', store=True,
                                   help="the warehouse to consider for the route selection on the next procurement (if any).")
    rpa_process_type = fields.Selection([
        ("all", "Pack All"),
        ("is_separate_box", "Is Separate Box"),
        ("individual_separate_multi_box", "Individual Separate Multi Box"),
        ("individual_item_same_box", "Individual Item Same Box"),
        ("split_multi_box", "Split Multi Box"),
        ("mixed", "Mixed")], copy=False, string="RPA Process Type")


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    goflow_box_id = fields.Char(copy=False)
    weight = fields.Float(related="product_id.weight")
    product_length = fields.Float(related="product_id.product_length")
    product_width = fields.Float(related="product_id.product_width")
    product_height = fields.Float(related="product_id.product_height")
    package_type_id = fields.Many2one('stock.package.type', related="product_packaging_id.package_type_id")
    rpa_process_type = fields.Selection([
        ("all", "Pack All"),
        ("is_separate_box", "Is Separate Box"),
        ("individual_separate_multi_box", "Individual Separate Multi Box"),
        ("individual_item_same_box", "Individual Item Same Box"),
        ("split_multi_box", "Split Multi Box"),
        ("mixed", "Mixed")], copy=False, string="RPA Process Type")


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    goflow_store_id = fields.Many2one(related="stock_move_id.goflow_store_id", store=True, copy=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_odoo_product_qty(self, product_id, location_id):
        product_qty = self.env['stock.quant'].search([
            ('product_id', '=', product_id.id),
            ('location_id', '=', location_id.id)], limit=1)
        if product_qty:
            qty = product_qty.quantity
        else:
            qty = 0
        return qty


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    warehouse_id = fields.Many2one('stock.warehouse', related='location_id.warehouse_id', store=True)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    api_shipping_request = fields.Boolean()


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    carrier_code = fields.Char('Code')


# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', store=True)


class ShippingDocuments(models.Model):
    _name = 'shipping.documents'

    picking_id = fields.Many2one('stock.picking', string='Picking')
    delivery_picking_id = fields.Many2one('stock.picking', string='Picking')
    call_auto_print = fields.Boolean(string="Auto Print")
    shipping_file_name = fields.Char(string='Name')
    file_content = fields.Binary(string='Shipping Document')
