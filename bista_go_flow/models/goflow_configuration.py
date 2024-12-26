# -*- coding: utf-8 -*-
import json

import requests

from odoo import models, fields
from .connection import GoFlowConnection
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class GoFlowConfiguration(models.Model):
    _name = 'goflow.configuration'
    _description = 'GoFlow Configuration'
    _rec_name = 'name'

    name = fields.Char(string='Instance Name')
    operations_state = fields.Boolean(string='Operations State')
    state = fields.Selection([
        ('draft', 'Not Confirmed'),
        ('done', 'Confirmed')], string='State', default='draft')
    # download_product_url = fields.Char(string='Product Data URL')
    download_warehouse_url = fields.Char(string='Warehouse Data URL')
    download_channel_url = fields.Char(string='Channel Data URL')
    access_token = fields.Char(string='Goflow Access Token')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.ref('base.main_company'))
    error_notification_send = fields.Boolean(string='Send Notification Error')
    user_id = fields.Many2one('res.users', string='User to send Notification')
    notification_send_by_sms = fields.Boolean(string='SMS')
    notification_send_by_email = fields.Boolean(string='Email')
    x_beta_contact_email = fields.Char(string='X-Beta-Contact Email')
    sale_order_import_operation = fields.Boolean(string='Sales Orders')
    invoice_matching = fields.Boolean(string='Invoice Matching')
    product_import_operation = fields.Boolean(string='Products')
    vendor_sync_operation = fields.Boolean(string='Vendors')
    tracking_data_export_operation = fields.Boolean(string='Shipment')
    inventory_export_operation = fields.Boolean(string='Inventory')
    manage_routing = fields.Boolean(string='Manage Routing')
    default_instance = fields.Boolean('Default Instance')

    # Download Sales Order Fields
    use_remote_so_id = fields.Boolean(string='Use Remote SO ID')
    default_delivery_carrier_id = fields.Many2one('delivery.carrier', string='Default Shipping Method')
    default_product_id = fields.Many2one('product.product', string='Fallback Product')
    last_order_import_date = fields.Datetime(string='Last Imported Order Date')
    order_as_historical = fields.Selection([
        ('all', 'All'),
        ('orders_with_creation_date_before', 'Orders with creation date before')],
        string='Import Orders as Historical')
    order_create_date = fields.Datetime(string='Order Creation Date Before')
    generated_delivery_slip = fields.Boolean(string='Generated Delivery Slip')
    channel_delivery_slip = fields.Boolean(string='Channel Delivery Slip')
    preferred_delivery_slip = fields.Selection([
        ('generated_delivery_slip', 'Generated Delivery Slip'),
        ('channel_delivery_slip', 'Channel Delivery Slip')],
        string='Preferred Delivery Slip')
    auto_import_sale_orders = fields.Boolean(string='Sync interval')
    auto_import_sale_orders_interval_number = fields.Integer()
    auto_import_sale_orders_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])
    auto_import_sale_orders_next_execution = fields.Datetime(string='Auto Next Sale Execution')
    auto_import_sale_order_user_id = fields.Many2one('res.users', string='Auto Import Sale Order User')

    sync_sale_order_filter = fields.Char(string="Custom Filter")
    active = fields.Boolean(string="Connection Active",default=True)
    
    is_sync_inventory = fields.Boolean(string="Is Sync Inventory?")
    cancel_goflow_order = fields.Boolean(string="Cancel Goflow Order?")
    goflow_sync_date = fields.Datetime()

    goflow_sync_shipment = fields.Boolean(string="Sync Shipment?")
    goflow_get_document = fields.Boolean(string="Get Documents?")
    goflow_order_review = fields.Boolean(string="Check Need to Review")
    goflow_order_review_sync_date = fields.Datetime(string="Order to Review Date")
    sync_order_review_filter = fields.Char(string="Custom Filter")
    sync_order_cancel_filter = fields.Char(string="Custom Filter")

    goflow_pick_date = fields.Datetime(string="GoFlow Split Order Date")

    # Download Product Fields
    # auto_create_product = fields.Boolean(string='Auto create if not found')
    # download_kit_and_group_product = fields.Boolean(string='Kit & Group Products')
    # auto_import_product = fields.Boolean(string='Sync interval')
    # auto_import_product_interval_number = fields.Integer()
    # auto_import_product_interval_type = fields.Selection([
    #     ('minutes', 'Minutes'),
    #     ('hours', 'Hours'),
    #     ('days', 'Days'),
    #     ('weeks', 'Weeks'),
    #     ('months', 'Months')])
    # auto_import_product_next_execution = fields.Datetime(string='Auto Next Product Execution')
    # auto_import_product_user_id = fields.Many2one('res.users', string='Auto Import Product User')
    # auto_map_product = fields.Boolean(string='Auto Map Product')
    # map_line_ids = fields.One2many('goflow.product.map.line', 'goflow_configuration_id', string='Line')

    # Download Vendor Fields
    sync_vendors = fields.Boolean(string='Sync Vendors')
    # auto_create_vendor = fields.Boolean(string='Auto create if not found')
    # download_kit_and_group_vendor = fields.Boolean(string='Kit & Group Vendors')
    # auto_import_vendor = fields.Boolean(string='Sync interval')
    # auto_import_vendor_interval_number = fields.Integer()
    # auto_import_vendor_interval_type = fields.Selection([
    #     ('minutes', 'Minutes'),
    #     ('hours', 'Hours'),
    #     ('days', 'Days'),
    #     ('weeks', 'Weeks'),
    #     ('months', 'Months')])
    # auto_import_vendor_next_execution = fields.Datetime(string='Auto Next Vendor Execution')
    # auto_import_vendor_user_id = fields.Many2one('res.users', string='Auto Import Vendor User')
    # auto_map_vendor = fields.Boolean(string='Auto Map Vendor')
    # map_line_ids = fields.One2many('goflow.vendor.map.line', 'goflow_configuration_id', string='Line')

    # Upload Tracking Data Fields
    notify_store_export_shipment = fields.Boolean(string='Notify Store While Export Shipment?')
    shipping_weight_measure = fields.Selection([
        ('pounds', 'Pounds'),
        ('ounces', 'Ounces')], string='Shipping Weight')
    auto_export_tracking = fields.Boolean(string='Sync interval')
    auto_export_tracking_interval_number = fields.Integer()
    auto_export_tracking_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])
    auto_export_tracking_next_execution = fields.Datetime(string='Auto Next Export Tracking Execution')
    auto_export_tracking_user_id = fields.Many2one('res.users', string='Auto Export Tracking User')

    # Upload Inventory Data Fields
    is_stock_safety_levels = fields.Boolean(string='Stock Safety Levels')
    stock_safety_levels = fields.Selection([
        ("not_upload_x_qty", "Don't upload the last x Qty"),
        ("not_upload_per_qty", "Don't upload the last %")])
    stock_safety_qty = fields.Float(string='Qty')
    auto_export_inventory = fields.Boolean(string='Sync interval')
    auto_export_inventory_interval_number = fields.Integer()
    auto_export_inventory_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])
    auto_export_inventory_next_execution = fields.Datetime(string='Auto Next Export Inventory Execution')
    auto_export_inventory_user_id = fields.Many2one('res.users', string='Auto Export Inventory User')

    # Invoice Matching Fields
    invoice_prefix = fields.Char(string='Invoice Prefix')
    auto_invoice_matching = fields.Boolean(string='Sync interval')
    auto_invoice_matching_interval_number = fields.Integer()
    auto_invoice_matching_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])
    auto_invoice_matching_next_execution = fields.Datetime(string='Auto Next Invoice Matching Execution')
    auto_invoice_matching_user_id = fields.Many2one('res.users', string='Auto Invoice Matching User ')
    auto_invoice_matching_timeout_interval_number = fields.Integer()
    auto_invoice_matching_timeout_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])

    # Routing Fields
    default_freight_class = fields.Float(string='Default Freight Class')
    auto_request_sync_interval = fields.Boolean(string='Auto Request - Sync interval')
    auto_request_interval_number = fields.Integer()
    auto_request_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])
    auto_request_next_execution = fields.Datetime(string='Auto Request Next Execution')
    auto_request_user_id = fields.Many2one('res.users', string='Auto Request User')
    auto_fetch_response_sync_interval = fields.Boolean(string='Auto fetch response - Sync interval')
    auto_fetch_response_interval_number = fields.Integer()
    auto_fetch_response_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])
    auto_fetch_response_next_execution = fields.Datetime(string='Auto fetch response Next Execution')
    auto_fetch_response_user_id = fields.Many2one('res.users', string='Auto fetch response User')
    auto_fetch_response_timeout_interval_number = fields.Integer()
    auto_fetch_response_timeout_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])

    sync_purchase_order = fields.Boolean(string="Sync Purchase Order")
    sync_purchase_order_filter = fields.Char(string="Custom Filter")

    warehouse_sync_operation = fields.Boolean(string="Warehouses")
    create_new_warehouse = fields.Boolean(string="Want to create Non-Existing Warehouse?")

    def goflow_reset_connection(self):
        self.write({'state': 'draft', 'active': True})

    def goflow_test_connection(self):
        self.write({'state': 'done', 'active': True})

        # return True

    # def _auto_goflow_download_products_data(self):
    #     goflow_configurration_ids = self.env['goflow.configuration'].search([])
    #     for each in goflow_configurration_ids:
    #         each.goflow_download_products_data()
    #
    # def goflow_download_products_data(self):
    #     x_beta_contact = self.x_beta_contact_email
    #     authorization = self.access_token
    #     goflow_login_url = self.download_product_url
    #     config_id = self
    #     goflow_connection_obj = GoFlowConnection.establish_connection(x_beta_contact, authorization, goflow_login_url,
    #                                                                   config_id)
    #     goflow_product_obj = self.env['goflow.product']
    #     for each in goflow_connection_obj:
    #         product_external_id = int(each.get('id', ''))
    #         name = each.get('details').get('name', '')
    #         item_number = each.get('item_number', '')
    #         type = each.get('type', '')
    #         status = each.get('status', '')
    #         goflow_product_id = (goflow_product_obj.search(
    #             [('product_external_id', '=', product_external_id)])) if product_external_id else False
    #         if goflow_product_id:
    #             update_values = {}
    #             if name and name != goflow_product_id.name:
    #                 update_values.update({'name': name})
    #             if item_number and item_number != goflow_product_id.item_number:
    #                 update_values.update({'item_number': item_number})
    #             if type and type != goflow_product_id.type:
    #                 update_values.update({'type': type})
    #             if status and status != goflow_product_id.status:
    #                 update_values.update({'status': status})
    #             if update_values:
    #                 update_values.update({'data': each})
    #                 goflow_product_id.write(update_values)
    #             product_id = self.env['product.product'].search([('default_code', '=', goflow_product_id.item_number)])
    #             if product_id:
    #                 goflow_product_id.write({'product_id': product_id.id})
    #         else:
    #             product_id = False
    #             if item_number:
    #                 product_id = self.env['product.product'].search([('default_code', '=', item_number)])
    #             goflow_product_obj.create({'product_id': product_id.id if product_id else False,
    #                                        'name': name,
    #                                        'item_number': item_number,
    #                                        'type': type,
    #                                        'status': status,
    #                                        'configuration_id': config_id.id,
    #                                        'product_external_id': product_external_id,
    #                                        'data': each})

    def _auto_goflow_sync_vendors_data(self):
        goflow_configurration_ids = self.env['goflow.configuration'].search(
            [('active', '=', True), ('state', '=', 'done'), ('vendor_sync_operation', '=', True)])
        for each in goflow_configurration_ids:
            each.goflow_sync_vendors_data()

    def goflow_sync_vendors_data(self):
        config_id = self
        if self.vendor_sync_operation:
            response = self._send_goflow_request('get', '/v1/vendors', payload=False)
            if response:
                vendor_response = response.json()
                goflow_vendor_obj = self.env['goflow.vendor']
                currency_obj = self.env['res.currency']
                if vendor_response.get('data'):
                    for each_vendor in vendor_response.get('data'):
                        goflow_vendor_id = each_vendor.get('id', False)
                        name = each_vendor.get('name', '')
                        status = each_vendor.get('status', '')
                        currency = each_vendor.get('currency', False)
                        currency_id = currency_obj.search([('name', 'ilike', currency)])
                        # tags = list(map(lambda d: d['name'], each_vendor.get('tags', False)))
                        notes = each_vendor.get('notes', '')
                        note = ''
                        for line in notes:
                            note += "\n " + line.get('text')
                        goflow_vendor = goflow_vendor_obj.search([('goflow_vendor_id', '=', goflow_vendor_id)])

                        if goflow_vendor:
                            update_values = {}
                            partner_values = {}
                            if name and name != goflow_vendor.name:
                                update_values.update({'name': name})
                                partner_values.update({'name': name})
                            if status and status != goflow_vendor.status:
                                update_values.update({'status': status})
                                partner_values.update({'active': status})
                            if currency_id and currency_id != goflow_vendor.currency:
                                update_values.update({'currency': currency_id.id})
                                partner_values.update({'currency_id': currency_id.id})
                            # if tags and tags != goflow_vendor.tags:
                            #     update_values.update({'tags': [(4, tags)]})
                            #     partner_values.update({'category_id': [(4, tags)]})
                            if note and note != goflow_vendor.notes:
                                update_values.update({'notes': note})
                                partner_values.update({'comment': note})
                            if vendor_response and vendor_response != goflow_vendor.vendor_data:
                                update_values.update({'vendor_data': vendor_response})
                            if update_values:
                                goflow_vendor.write(update_values)
                            if partner_values:
                                goflow_vendor.partner_id.write(partner_values)
                        else:
                            partner_values = {
                                'name': name,
                                'active': True if status == 'active' else False,
                                'currency_id': currency_id.id,
                                'supplier_rank': 1,
                                # 'category_id': [(4, tags)],
                            }
                            partner_id = self.create_partner(partner_values, False, False, )
                            goflow_vendor_values = {
                                'goflow_vendor_id': goflow_vendor_id,
                                'name': name,
                                'status': status,
                                'notes': note,
                                'currency': currency_id.id if currency_id else False,
                                # 'tags': [(4, tags)],
                                'partner_id': partner_id.id if partner_id else False,
                                'vendor_data': vendor_response,
                                'configuration_id': config_id.id,
                            }
                            self.create_goflow_vendor(goflow_vendor_values)

    # Scheduled Action has been commented due to requirement changes : 20112023 - Hemant Bhoi
    # def _auto_goflow_sync_warehouse_data(self):
    #     goflow_configurration_ids = self.env['goflow.configuration'].search(
    #         [('state', '=', 'draft'), ('warehouse_sync_operation', '=', True)])
    #     for each in goflow_configurration_ids:
    #         each.goflow_sync_warehouse_data()
    #
    # Scheduled Action has been commented due to requirement changes : 20112023 - Hemant Bhoi
    # def goflow_sync_warehouse_data(self):
    #     config_id = self
    #     response = self._send_goflow_request('get', '/v1/warehouses', payload=False)
    #     if response:
    #         warehouse_response = response.json()
    #         goflow_warehouse_obj = self.env['goflow.warehouse']
    #         state_obj = self.env['res.country.state']
    #         country_obj = self.env['res.country']
    #         if warehouse_response.get('data'):
    #             for each_wh in warehouse_response.get('data'):
    #                 goflow_warehouse_id = each_wh.get('id', '')
    #                 goflow_warehouse_name = each_wh.get('name', '')
    #                 goflow_warehouse_type = each_wh.get('type', '')
    #                 goflow_warehouse_address = each_wh.get('address', '')
    #                 country_id = country_obj.search([('code', '=', goflow_warehouse_address.get('country_code'))])
    #                 state_id = state_obj.search(
    #                     [('code', '=', goflow_warehouse_address.get('state')), ('country_id', '=', country_id.id)])
    #                 goflow_warehouse_obj_id = goflow_warehouse_obj.search(
    #                     [('goflow_warehouse_id', '=', goflow_warehouse_id)]) if goflow_warehouse_id else False
    #                 if goflow_warehouse_obj_id:
    #                     update_values = {}
    #                     wh_values = {}
    #                     partner_vals = {}
    #                     if goflow_warehouse_name and goflow_warehouse_name != goflow_warehouse_obj_id.goflow_warehouse_name:
    #                         update_values.update({'goflow_warehouse_name': goflow_warehouse_name})
    #                         wh_values.update({'name': goflow_warehouse_name})
    #
    #                     if goflow_warehouse_address.get('company') and goflow_warehouse_address.get('company') != goflow_warehouse_obj_id.partner_id.name:
    #                         partner_vals.update({'name': goflow_warehouse_address.get('company')})
    #
    #                     if goflow_warehouse_address.get('street1') and goflow_warehouse_address.get('street1') != goflow_warehouse_obj_id.partner_id.street:
    #                         partner_vals.update({'street': goflow_warehouse_address.get('street1')})
    #
    #                     if goflow_warehouse_address.get('street2') and goflow_warehouse_address.get('street2') != goflow_warehouse_obj_id.partner_id.street2:
    #                         partner_vals.update({'street2': goflow_warehouse_address.get('street2')})
    #
    #                     if goflow_warehouse_address.get('city') and goflow_warehouse_address.get('city') != goflow_warehouse_obj_id.partner_id.city:
    #                         partner_vals.update({'city': goflow_warehouse_address.get('city')})
    #
    #                     if state_id and state_id != goflow_warehouse_obj_id.partner_id.state_id:
    #                         partner_vals.update({'state_id': state_id})
    #
    #                     if country_id and country_id != goflow_warehouse_obj_id.partner_id.country_id:
    #                         partner_vals.update({'country_id': country_id})
    #
    #                     if goflow_warehouse_address.get('zip') and goflow_warehouse_address.get('zip') != goflow_warehouse_obj_id.partner_id.zip:
    #                         partner_vals.update({'zip': goflow_warehouse_address.get('zip')})
    #
    #                     if goflow_warehouse_address.get('email') and goflow_warehouse_address.get('email') != goflow_warehouse_obj_id.partner_id.email:
    #                         partner_vals.update({'email': goflow_warehouse_address.get('email')})
    #
    #                     if goflow_warehouse_address.get('phone') and goflow_warehouse_address.get('phone') != goflow_warehouse_obj_id.partner_id.phone:
    #                         partner_vals.update({'phone': goflow_warehouse_address.get('phone')})
    #
    #                     if update_values:
    #                         update_values.update({'goflow_warehouse_data': each_wh})
    #                         goflow_warehouse_obj_id.write(update_values)
    #
    #                     if wh_values:
    #                         goflow_warehouse_obj_id.warehouse_id.write(wh_values)
    #                     if partner_vals:
    #                         goflow_warehouse_obj_id.partner_id.write(partner_vals)
    #                 else:
    #                     partner_values = {
    #                         'name': goflow_warehouse_address.get('company'),
    #                         'is_company': True,
    #                         'street': goflow_warehouse_address.get('street1'),
    #                         'street2': goflow_warehouse_address.get('street2'),
    #                         'city': goflow_warehouse_address.get('city'),
    #                         'state_id': state_id.id if state_id else False,
    #                         'country_id': country_id.id if country_id else False,
    #                         'zip': goflow_warehouse_address.get('zip_code'),
    #                         'email': goflow_warehouse_address.get('email'),
    #                         'phone': goflow_warehouse_address.get('phone'),
    #                     }
    #                     partner_id = self.create_partner(partner_values, False, False)
    #
    #                     warehouse_values = {
    #                         'name': goflow_warehouse_name,
    #                         'partner_id': partner_id.id,
    #                     }
    #                     warehouse_id = self.create_warehouse(warehouse_values)
    #
    #                     goflow_warehouse_values = {'goflow_warehouse_id': goflow_warehouse_id,
    #                                                'goflow_warehouse_name': goflow_warehouse_name,
    #                                                'partner_id': partner_id.id,
    #                                                'configuration_id': config_id.id,
    #                                                'goflow_warehouse_data': each_wh,
    #                                                'company_id': config_id.company_id.id,
    #                                                'warehouse_id': warehouse_id.id,
    #                                                'warehouse_type': goflow_warehouse_type,
    #                                                }
    #                     self.create_goflow_warehouse(goflow_warehouse_values)

    def _auto_goflow_download_channel_data(self):
        goflow_configurration_ids = self.env['goflow.configuration'].search([])
        for each in goflow_configurration_ids:
            each.goflow_download_channel_data()

    def goflow_download_channel_data(self):
        config_id = self
        goflow_connection = self._send_goflow_request('get', '/v1/stores', payload=False)
        goflow_connection_obj = goflow_connection.json()
        goflow_channel_obj = self.env['goflow.channel']
        goflow_store_obj = self.env['goflow.store']
        for each in goflow_connection_obj.get('data', []):
            goflow_store_id = each.get('id', '')
            goflow_store_name = each.get('name', '')
            goflow_channel_name = each.get('channel', '')
            goflow_channel_obj_id = (
                goflow_channel_obj.search([('goflow_store_id', '=', goflow_store_id)])) if goflow_store_id else False
            if goflow_channel_obj_id:
                update_values = {}
                if goflow_store_name and goflow_store_name != goflow_channel_obj_id.goflow_store_name:
                    update_values.update({'goflow_store_name': goflow_store_name})
                if goflow_channel_name and goflow_channel_name != goflow_channel_obj_id.goflow_channel_name:
                    update_values.update({'goflow_channel_name': goflow_channel_name})
                if update_values:
                    goflow_channel_obj_id.write(update_values)
                partner_id = self.env['res.partner'].search([('name', '=', goflow_channel_obj_id.goflow_store_name)])
                if partner_id:
                    goflow_channel_obj_id.write({'partner_id': partner_id.id})
            else:
                partner_id = self.env['res.partner'].search([('name', '=', goflow_store_name)])
                goflow_channel_obj.create({'goflow_store_id': goflow_store_id,
                                           'goflow_store_name': goflow_store_name,
                                           'goflow_channel_name': goflow_channel_name,
                                           'configuration_id': config_id.id,
                                           'partner_id': partner_id.id if partner_id else False})

            store = goflow_store_obj.search([('store_id','=', goflow_store_id)])
            if not store:
                self.env['goflow.order']._create_store(each)

    # def _add_goflow_log(self, method, query_url, response, payload, exception):
    #     try:
    #         message = response.json()
    #     except Exception as e:
    #         try:
    #             message = response.text
    #         except Exception as e:
    #             message = response
    #
    #     self.env['goflow.error.log'].sudo().create(
    #         {'name': 'goflow_request_log',
    #          'message': message,
    #          'api_url': query_url,
    #          'request': json.dumps(query_url, default=str),
    #          'request_type': method,
    #          'request_payload': payload,
    #          'response': response if not exception else False,
    #          'status': response.status_code if not exception else False})

    def _add_goflow_log(self, method, query_url, response, payload, exception):
        try:
            if 'application/json' in response.headers.get('Content-Type', ''):
                message = response.json()
            else:
                message = response.text
        except Exception as e:
            message = f"Error retrieving response content: {str(e)}"

        log_values = {
            'name': 'goflow_request_log',
            'message': message,
            'api_url': query_url,
            'request': json.dumps(query_url, default=str),
            'request_type': method,
            'request_payload': payload,
            'response': response if not exception else False,
            'status': response.status_code if not exception else False
        }

        self.env['goflow.error.log'].sudo().create(log_values)
        self.env.cr.commit()

    def _send_goflow_request(self, method, query_url, payload=False):
        x_beta_contact = self.x_beta_contact_email
        authorization = self.access_token
        goflow_login_url = self.download_channel_url
        headers = {
            'X-Beta-Contact': x_beta_contact,
            'Authorization': 'Bearer ' + authorization
        }
        # payload = json.dumps(payload)
        query_url = goflow_login_url + query_url
        response = ''
        try:
            response = requests.request(method, query_url, json=payload, headers=headers)
            self._add_goflow_log(method, query_url, response, payload, exception=False)
        except Exception as e:
            self._add_goflow_log(method, query_url, str(e), payload, exception=True)
        return response

    def goflow_get_bulk_purchase(self):
        self.env['goflow.purchase.order'].get_bulk_purchase_order()

    def goflow_get_bulk_sale(self):
        self.env['goflow.order'].get_bulk_sale_order()

    def create_partner(self, values, billing_address=False, shipping_address=False):
        partner_obj = self.env['res.partner']
        partner_id = partner_obj.create(values)
        return partner_id

    def create_goflow_vendor(self, values):
        vendor_obj = self.env['goflow.vendor']
        goflow_vendor = vendor_obj.create(values)
        return goflow_vendor

    def create_warehouse(self, values):
        wh_obj = self.env['stock.warehouse']
        wh = wh_obj.with_context({'goflow_warehouse': True}).create(values)
        return wh

    def create_goflow_warehouse(self, values):
        goflow_wh_obj = self.env['goflow.warehouse']
        goflow_wh = goflow_wh_obj.create(values)
        return goflow_wh

    def sync_warehouses(self):
        response = self._send_goflow_request('get', '/v1/warehouses', payload=False)
        if response:
            warehouse_response = response.json()
            goflow_warehouse_obj = self.env['goflow.warehouse']
            state_obj = self.env['res.country.state']
            country_obj = self.env['res.country']
            if warehouse_response.get('data'):
                for each_wh in warehouse_response.get('data'):
                    goflow_warehouse_id = each_wh.get('id', '')
                    goflow_warehouse_name = each_wh.get('name', '')
                    goflow_warehouse_type = each_wh.get('type', '')
                    goflow_warehouse_address = each_wh.get('address', '')
                    country_code = goflow_warehouse_address.get('country_code') or 'US'
                    country_id = country_obj.search([('code', '=', country_code)])
                    state_id = state_obj.search([('code', '=', goflow_warehouse_address.get('state')),
                                                 ('country_id', '=', country_id.id)])
                    goflow_warehouse_obj_id = goflow_warehouse_obj.search(
                        [('goflow_warehouse_id', '=', goflow_warehouse_id)]) if goflow_warehouse_id else False
                    if goflow_warehouse_obj_id:
                        update_values = {}
                        wh_values = {}
                        partner_vals = {}
                        if goflow_warehouse_name and goflow_warehouse_name != goflow_warehouse_obj_id.goflow_warehouse_name:
                            update_values.update({'goflow_warehouse_name': goflow_warehouse_name})
                            wh_values.update({'name': goflow_warehouse_name})

                        if goflow_warehouse_address.get('company') and goflow_warehouse_address.get(
                                'company') != goflow_warehouse_obj_id.partner_id.name:
                            partner_vals.update({'name': goflow_warehouse_address.get('company')})

                        if goflow_warehouse_address.get('street1') and goflow_warehouse_address.get(
                                'street1') != goflow_warehouse_obj_id.partner_id.street:
                            partner_vals.update({'street': goflow_warehouse_address.get('street1')})

                        if goflow_warehouse_address.get('street2') and goflow_warehouse_address.get(
                                'street2') != goflow_warehouse_obj_id.partner_id.street2:
                            partner_vals.update({'street2': goflow_warehouse_address.get('street2')})

                        if goflow_warehouse_address.get('city') and goflow_warehouse_address.get(
                                'city') != goflow_warehouse_obj_id.partner_id.city:
                            partner_vals.update({'city': goflow_warehouse_address.get('city')})

                        if state_id and state_id != goflow_warehouse_obj_id.partner_id.state_id:
                            partner_vals.update({'state_id': state_id})

                        if country_id and country_id != goflow_warehouse_obj_id.partner_id.country_id:
                            partner_vals.update({'country_id': country_id})

                        if goflow_warehouse_address.get('zip') and goflow_warehouse_address.get(
                                'zip') != goflow_warehouse_obj_id.partner_id.zip:
                            partner_vals.update({'zip': goflow_warehouse_address.get('zip')})

                        if goflow_warehouse_address.get('email') and goflow_warehouse_address.get(
                                'email') != goflow_warehouse_obj_id.partner_id.email:
                            partner_vals.update({'email': goflow_warehouse_address.get('email')})

                        if goflow_warehouse_address.get('phone') and goflow_warehouse_address.get(
                                'phone') != goflow_warehouse_obj_id.partner_id.phone:
                            partner_vals.update({'phone': goflow_warehouse_address.get('phone')})

                        if update_values:
                            update_values.update({'goflow_warehouse_data': each_wh})
                            goflow_warehouse_obj_id.write(update_values)

                        if wh_values:
                            goflow_warehouse_obj_id.warehouse_id.write(wh_values)
                        # if partner_vals:
                        #     goflow_warehouse_obj_id.partner_id.write(partner_vals)
                    else:
                        stock_warehouse = self.env['stock.warehouse'].search(['|',
                            ('name', '=', goflow_warehouse_name),
                            ('code', '=', goflow_warehouse_name)])
                        if stock_warehouse:
                            goflow_warehouse_values = {
                                'goflow_warehouse_id': goflow_warehouse_id,
                                'goflow_warehouse_name': goflow_warehouse_name,
                                'partner_id': stock_warehouse.partner_id.id,
                                'configuration_id': self.id,
                                'goflow_warehouse_data': each_wh,
                                'company_id': self.company_id.id,
                                'warehouse_id': stock_warehouse.id,
                                'warehouse_type': goflow_warehouse_type,
                            }
                            new_goflow_warehouse = self.create_goflow_warehouse(goflow_warehouse_values)
                        else:
                            if self.create_new_warehouse:
                                partner_values = {
                                    'name': goflow_warehouse_address.get('company'),
                                    'is_company': True,
                                    'street': goflow_warehouse_address.get('street1'),
                                    'street2': goflow_warehouse_address.get('street2'),
                                    'city': goflow_warehouse_address.get('city'),
                                    'state_id': state_id.id if state_id else False,
                                    'country_id': country_id.id if country_id else False,
                                    'zip': goflow_warehouse_address.get('zip_code'),
                                    'email': goflow_warehouse_address.get('email'),
                                    'phone': goflow_warehouse_address.get('phone'),
                                }
                                partner_id = self.create_partner(partner_values, False, False)

                                warehouse_values = {
                                    'name': goflow_warehouse_name,
                                    'partner_id': partner_id.id,
                                }
                                warehouse_id = self.create_warehouse(warehouse_values)

                                goflow_warehouse_values = {
                                    'goflow_warehouse_id': goflow_warehouse_id,
                                    'goflow_warehouse_name': goflow_warehouse_name,
                                    'partner_id': partner_id.id,
                                    'configuration_id': self.id,
                                    'goflow_warehouse_data': each_wh,
                                    'company_id': self.company_id.id,
                                    'warehouse_id': warehouse_id.id,
                                    'warehouse_type': goflow_warehouse_type,
                                }
                                new_goflow_warehouse = self.create_goflow_warehouse(goflow_warehouse_values)

    # date converion
    
    def convert_goflow_date_to_odoo_format(self,date):
        converted_date = datetime.fromisoformat(date[:19])
        return converted_date

    def convert_odoo_date_to_goflow_format(self,date):
        converted_date = date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        return converted_date
