# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, models, fields, _
import logging
import requests
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

_logger = logging.getLogger(__name__)


class RithumConfig(models.Model):
    _name = 'rithum.config'
    _description = "Rithum Configuration"

    name = fields.Char("Name", required=True)
    state = fields.Selection([('draft', 'Draft'), ('success', 'Success'),
                              ('fail', 'Fail')],
                             string='Status',
                             help='Connection status of records',
                             default='draft')
    active = fields.Boolean(string='Active',
                            default="True",
                            help='Active/Inactive Rithum config.')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    auth_token = fields.Char("Token", copy=False, required=True)
    client_id = fields.Char("Client ID", copy=False)
    client_key = fields.Char("Client Key", copy=False)
    rithum_customer_id = fields.Many2one('res.partner', string="Customer", required=True)
    last_import_order_date = fields.Datetime(string='Last Order Import Date')
    consider_days = fields.Integer("Consider days", default=1)
    rithum_warehouse = fields.Char("Warehouse", default='003', copy=False, required=True)
    auto_confirm_order = fields.Boolean("Auto Confirm Orders", default=False)

    def rithum_archive_active(self):
        """This method will set the Rithum config to archive/active"""
        if self.active:
            self.update({"active": False,
                         'state': 'draft'})
        else:
            self.update({"active": True})

    def rithum_base_url(self):
        return "https://api.dsco.io/api/v3"

    def rithum_acknowledge_order_url(self):
        return self.rithum_base_url() + '/order/acknowledge'

    def rithum_get_order_url(self):
        return self.rithum_base_url() + '/order'

    def rithum_shiment_order_url(self):
        return self.rithum_base_url() + '/order/singleShipment'

    def rithum_invoice_order_url(self):
        return self.rithum_base_url() + '/invoice'

    def rithum_inventory_update_url(self):
        return self.rithum_base_url() + '/inventory/batch/small'

    def rithum_cancel_order_url(self):
        return self.rithum_base_url() + '/order/item/cancel'

    def rithum_auth_token(self):
        if self.auth_token:
            return "bearer " + self.auth_token
        else:
            raise ValidationError(_("Please add token"))

    def action_test_connection(self):
        if self.auth_token:
            url = self.rithum_base_url() + "/hello"
            rithum_token = self.rithum_auth_token()
            headers = {
                'Connection': 'keep-alive',
                'Accept': 'application/json',
                'Authorization': rithum_token,
                'Content-Type': 'application/json',
            }
            payload = {}
            response = requests.get(url, data=payload, headers=headers)
            if response.status_code == 200:
                self.state = 'success'
                if self._context.get('from_import_action'):
                    _logger.info('\n---------- Connected successfully ------------')
                else:
                    return {
                        'effect': {
                            'fadeout': 'slow',
                            'message': 'connection successful',
                            'type': 'rainbow_man',
                        }
                    }
            else:
                self.state = 'fail'
                if self._context.get('from_import_action'):
                    _logger.error('\n--------- Connection Fail Invalid access token ---------')
                else:
                    return {"type": "ir.actions.client",
                            "tag": "display_notification",
                            "params": {"title": "Rithum",
                                       "message": "Test connection fail!",
                                       "sticky": False}}

    def action_import_order(self):
        for t_con in self.search([('state', '!=', 'success'), ('active', '=', True)]):
            t_con.with_context(from_import_action=True).action_test_connection()

        for config in self.search([('state', '=', 'success'), ('active', '=', True)], limit=1):
            from_date = config.last_import_order_date and config.last_import_order_date or datetime.now() - relativedelta(
                days=config.consider_days)
            to_date = datetime.now()
            url = config.rithum_base_url() + "/order/page"
            rithum_token = config.rithum_auth_token()
            order_headers = {
                'Connection': 'keep-alive',
                'Accept': 'application/json',
                'Authorization': rithum_token,
                'Content-Type': 'application/json',
            }
            params = {
                'ordersCreatedSince': from_date,
                'until': to_date,
                # 'includeTestOrders': 'false',
                'status': 'created'
            }
            response = requests.get(url, params=params, headers=order_headers)
            response_data = response.json()
            if response.status_code == 200:
                response_orders_vals = response_data.get('orders')
                create_order_ids = config.create_orders(response_orders_vals)
                if "scrollId" in response_data:
                    scroll = True
                    scroll_id = response_data.get('scrollId')
                    while (scroll):
                        response_orders = config.next_page(config, scroll_id)
                        create_order_ids |= config.create_orders(response_orders.get('orders'))
                        if not response_orders.get('scrollId'):
                            scroll = False
                        scroll_id = response_orders.get('scrollId')
                if config.auto_confirm_order and create_order_ids:
                    create_order_ids.with_context(from_auto_import=True).action_confirm()
                    self.update_rithum_acknowledge_order(sale_ids=create_order_ids, config_id=config)
                config.last_import_order_date = fields.Datetime.now()
                _logger.info('\n---------- Orders import successfully ------------')

            else:
                if isinstance(response_data.get('messages'), list) and 'description' in response_data.get('messages')[
                    0]:
                    error_desc = response_data.get('messages')[0].get('description')
                _logger.error('\nRithum Respone : %s', error_desc)

    def prepare_partner_values(self, partner_detail, po_number):
        error_log_obj = self.env['rithum.error.order.log']
        country_id = self.env['res.country'].search([('code', '=', partner_detail['country'])])
        prepare_error_vals = {
            'name': po_number,
        }
        if not country_id:
            prepare_error_vals.update({
                'error_message': "Invoice Partner Country is not available"
            })
        state_id = self.env['res.country.state'].search(
            [('country_id', '=', country_id.id), ('code', '=', partner_detail['state'])])
        if not state_id:
            prepare_error_vals.update({
                'error_message': "Invoice Partner state is not available"
            })
        if 'error' in prepare_error_vals:
            error_log_obj.create(prepare_error_vals)
            return {}
        values = {
            'name': partner_detail['name'],
            'street': partner_detail.get('address1', ''),
            'street2': partner_detail.get('address2', ''),
            'country_id': country_id.id,
            'state_id': state_id.id,
            'phone': partner_detail.get('phone', ''),
            'email': partner_detail.get('email', ''),
            'zip': partner_detail.get('postal', ''),
            'city': partner_detail.get('city', ''),
            'is_automatically_created': True
        }
        return values

    def prepare_sale_order_vals(self, resposne_data, rithum_shipping_partner_id):
        # prod_obj = self.env['product.product']
        rithum_prod_obj = self.env['rithum.product.product']
        error_log_obj = self.env['rithum.error.order.log']
        po_number = resposne_data['poNumber']
        order_lines = resposne_data['lineItems']
        order_line_vals = []
        sku_error_list = ''

        for line_val in order_lines:
            sku = line_val['sku']
            # product_id = prod_obj.search([('default_code', '=', sku)])
            rithum_product_id = rithum_prod_obj.search([('rithum_product_id', '=', sku)])
            # if not product_id:
            if not rithum_product_id:
                sku_error_list += f'{sku}, '
                print(f"\n\n\n\npo-{po_number}\nsku-{sku}\nerror-{sku_error_list}")
            else:
                order_line_vals.append((0, 0, {
                    # 'product_id': product_id.id,
                    'product_id': rithum_product_id.product_id.id,
                    'product_uom_qty': float(line_val['quantity']),
                    'price_unit': float(line_val['expectedCost'])
                }))
        # if self._context.get('from_error'):
        #     return {'error': sku_error_list}
        if sku_error_list:
            prepare_error_vals = {
                'name': po_number,
                'error_date': datetime.today(),
                'error_message': f"SKU : '{sku_error_list}' product is not sync in rithum product",
                'rithum_config_id': self.id
            }
            error_exsist = error_log_obj.search([('name', '=', po_number)])
            if not error_exsist:
                error_log_obj.create(prepare_error_vals)
            return {}
        order_vals = {
            'partner_id': self.rithum_customer_id.id,
            'partner_shipping_id': rithum_shipping_partner_id.id,
            'customer_po': po_number,
            'company_id': self.company_id.id,
            'payment_term_id': self.payment_term_id.id,
            'rithum_shipping_method_id': resposne_data['shipMethod'],
            'rithum_carrier_id': resposne_data['shipCarrier'],
            'ship_via': resposne_data['shipCarrier'] + " " + resposne_data['shipMethod'],
            'date_order': self.iso_date_convert(resposne_data['retailerCreateDate']),
            'commitment_date': self.iso_date_convert(resposne_data['shipByDate']),
            'allow_do_dropship': resposne_data.get('orderType') == 'dropship',
            'order_line': order_line_vals,
            'rithum_config_id': self.id,
            'is_free_shipping': True,
        }
        return order_vals

    def create_orders(self, response_orders_vals):
        order_val_list = []
        partner_obj = self.env['res.partner']
        sale_obj = self.env['sale.order']
        if isinstance(response_orders_vals, dict):
            response_orders_vals = [response_orders_vals]
        for data in response_orders_vals:
            if 'shipping' in data:
                partner_detail = data.get('shipping')
                po_number = data.get('poNumber')
                order_exist = sale_obj.search([('customer_po', '=', po_number), ('rithum_config_id', '!=', False)])
                if not order_exist:
                    partner_name = partner_detail['name']
                    rithum_shipping_partner_id = partner_obj.search([('name', '=', partner_name)], limit=1)
                    if not rithum_shipping_partner_id:
                        partner_vals = self.prepare_partner_values(partner_detail, po_number)
                        if partner_vals:
                            rithum_shipping_partner_id = partner_obj.create(partner_vals)
                    order_val = self.prepare_sale_order_vals(data, rithum_shipping_partner_id)
                    if order_val:
                        order_val_list.append(order_val)
        if order_val_list:
            orders = sale_obj.create(order_val_list)
            # self.env.cr.commit()
            return orders

    def create_orders_single_order(self, po_number):
        order_object_url = self.rithum_base_url() + "/order"
        rithum_token = self.rithum_auth_token()
        order_headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json',
            'Authorization': rithum_token,
            'Content-Type': 'application/json',
        }
        params = {
            'orderKey': 'poNumber',
            'value': po_number,
        }
        response = requests.get(order_object_url, params=params, headers=order_headers)
        if response.status_code == 200:
            response_data = response.json()
            order = self.create_orders(response_data)
            if order and self.auto_confirm_order:
                order.with_context(from_single=True).action_confirm()
                self.update_rithum_acknowledge_order(sale_ids=order, config_id=self)
                _logger.info(f'\n---------- Order for Po Number:{po_number} import successfully ------------')
            return order
        else:
            response_data = response.json()
            if isinstance(response_data.get('messages'), list) and 'description' in response_data.get('messages')[0]:
                error_desc = response_data.get('messages')[0].get('description')
                raise ValidationError(_(f"Response from Rithum: {error_desc}"))

    def iso_date_convert(self, date_val):
        parsed_date = datetime.fromisoformat(date_val)
        return parsed_date.strftime('%Y-%m-%d %H:%M:%S')

    def next_page(self, config, scroll_id):
        url = self.rithum_base_url() + "/order/page"
        rithum_token = config.rithum_auth_token()
        order_headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json',
            'Authorization': rithum_token,
            'Content-Type': 'application/json',
        }
        params = {
            'scrollId': scroll_id

        }
        response = requests.get(url, params=params, headers=order_headers)
        if response.status_code == 200:
            response_data = response.json()
            return response_data
        else:
            return {}

    def update_rithum_acknowledge_order(self, sale_ids, config_id):
        data = []
        rithum_update_url = config_id.rithum_acknowledge_order_url()
        rithum_token = config_id.rithum_auth_token()

        order_headers = {
            'Accept': 'application/json',
            'Authorization': rithum_token,
            'Content-Type': 'application/json',
        }
        for order in sale_ids:
            data.append({
                'type': 'PO_NUMBER',
                'id': order.customer_po,
            })
        response = requests.post(rithum_update_url, json=data, headers=order_headers)
        response_data = response.json()
        if response.status_code == 202:
            _logger.info(f'\n---------- Acknowledge Order successfully ------------')
        else:
            error_desc = response_data.get('messages')[0].get('description')
            raise ValidationError(_(f"Response from Rithum: {error_desc}"))

    def cancel_rithum_order_status(self, sale_id):
        rithum_po = sale_id.customer_po
        rithum_cancel_url = self.rithum_cancel_order_url()

        rithum_token = self.rithum_auth_token()
        order_headers = {
            'Accept': 'application/json',
            "Content-type": "application/json",
            'Authorization': rithum_token,
        }
        lineitems = []
        for line in sale_id.order_line:
            line_vals = {
                'cancelCode': 'CXSO',
                'cancelledReason': 'Cancel from odoo',
                'cancelledQuantity': line.product_uom_qty,
                'sku': line.product_id.default_code
            }
            lineitems.append(line_vals)

        params = {
            'type': 'PO_NUMBER',
            'id': rithum_po,
            'lineItems': lineitems,
        }
        response = requests.post(rithum_cancel_url, json=params, headers=order_headers)
        if response.status_code == 200:
            _logger.info(f'\n---------- Order {sale_id.name} cancel successfully ------------')
        else:
            response_data = response.json()
            if isinstance(response_data.get('messages'), list) and 'description' in response_data.get('messages')[0]:
                error_desc = response_data.get('messages')[0].get('description')
                raise ValidationError(_(f"Response from Rithum: {error_desc}"))

    def cancel_rithum_order_item(self, sale_id, cancel_move_ids):
        rithum_po = sale_id.customer_po
        rithum_cancel_url = self.rithum_cancel_order_url()

        rithum_token = self.rithum_auth_token()
        order_headers = {
            'Accept': 'application/json',
            "Content-type": "application/json",
            'Authorization': rithum_token,
        }
        lineitems = []
        for line in cancel_move_ids:
            line_vals = {
                'cancelCode': 'CXSO',
                'cancelledReason': 'Cancel from odoo',
                'cancelledQuantity': line.product_uom_qty,
                'sku': line.product_id.default_code
            }
            lineitems.append(line_vals)

        params = {
            'type': 'PO_NUMBER',
            'id': rithum_po,
            'lineItems': lineitems,
        }
        if lineitems:
            response = requests.post(rithum_cancel_url, json=params, headers=order_headers)
            if response.status_code == 200:
                _logger.info(f'\n---------- Order {sale_id.name} cancel successfully ------------')
            else:
                response_data = response.json()
                if isinstance(response_data.get('messages'), list) and 'description' in response_data.get('messages')[
                    0]:
                    error_desc = response_data.get('messages')[0].get('description')
                    raise ValidationError(_(f"Response from Rithum: {error_desc}"))

    def create_shipment_rithum_order(self, picking):
        rithum_prod_obj = self.env['rithum.product.product']

        sale_id = picking.sale_id
        shipping_from = sale_id.warehouse_id.partner_id
        shipping_to = picking.partner_id
        rithum_po = sale_id.customer_po
        rithum_shipment_url = self.rithum_shiment_order_url()
        rithum_token = self.rithum_auth_token()

        lineitems = []
        for line in picking.move_ids_without_package:
            rithum_product = rithum_prod_obj.search([('product_id', '=', line.product_id.id)], limit=1)
            if line.quantity_done >= 1:
                line_vals = {
                    # "sku": line.product_id.default_code,
                    "sku": rithum_product.rithum_product_id,
                    "quantity": line.quantity_done
                }
                lineitems.append(line_vals)

        shipping_carrier = sale_id.rithum_carrier_id
        shipMethod = sale_id.rithum_shipping_method_id
        if self._context.get('manual_validate_picking'):
            shipping_carrier = picking.carrier_id.name
            shipMethod = "-"
        if self._context.get('ship_station_sync_picking'):
            shipping_carrier = "-"
            shipMethod = picking.shipstation_service

        params = {
            "poNumber": rithum_po,
            "shipments": [
                {"lineItems": lineitems,
                 "shipFrom": {
                     "firstName": shipping_from.name,
                     "lastName": shipping_from.name,
                     "company": picking.company_id.name,
                     "address1": shipping_from.street,
                     "address2": shipping_from.street2,
                     "city": shipping_from.city,
                     "region": shipping_from.state_id.name,
                     "postal": shipping_from.zip,
                     "country": shipping_from.country_id.code,
                     "phone": shipping_from.phone,
                     "email": shipping_from.email,
                 },
                 "shipTo": {
                     "firstName": shipping_to.name,
                     "company": shipping_to.name,
                     "address1": shipping_to.street,
                     "address2": shipping_to.street2,
                     "city": shipping_to.city,
                     "region": shipping_to.state_id.name,
                     "postal": shipping_to.zip,
                     "country": shipping_to.country_id.code,
                     "phone": shipping_to.phone,
                     "email": shipping_to.email,
                     "name": shipping_to.display_name,
                 },
                 "shipWeight": picking.shipping_weight,
                 "shipWeightUnits": picking.weight_uom_name,
                 'trackingNumber': picking.carrier_tracking_ref,
                 "shipDate": str(picking.scheduled_date),
                 "currencyCode": sale_id.currency_id.name,
                 "shipCarrier": shipping_carrier,
                 "shipMethod": shipMethod
                 },
            ],
        }
        if lineitems:
            data = json.dumps(params)
            order_headers = {
                'Accept': 'application/json',
                'Content-type': 'application/json',
                'Authorization': rithum_token,
                'Content-Length': f'{len(str(data))}',
                'Host': 'api.dsco.io',
            }
            response = requests.post(rithum_shipment_url, data=data, headers=order_headers)
            if response.status_code == 201:
                _logger.info(f'\n---------- Shipment create for order {sale_id.name} successfully ------------')
            else:
                response_data = response.json()
                if isinstance(response_data.get('messages'), list) and 'description' in response_data.get('messages')[
                    0]:
                    error_desc = response_data.get('messages')[0].get('description')
                    raise ValidationError(_(f"During shipment create Response from Rithum: {error_desc}"))

    def create_invoice_rithum_order(self, invoice_id):
        rithum_prod_obj = self.env['rithum.product.product']
        sale_id = invoice_id.sale_order_id
        shipping_from = sale_id.warehouse_id.partner_id
        shipping_to = sale_id.partner_shipping_id
        rithum_po = sale_id.customer_po
        rithum_invoice_url = self.rithum_invoice_order_url()
        rithum_token = self.rithum_auth_token()

        payment_term_days = invoice_id.invoice_payment_term_id.line_ids and invoice_id.invoice_payment_term_id.line_ids[
            0].days or 0
        lineitems = []
        line_subtotal = 0
        lineNumber = 1
        for line in invoice_id.invoice_line_ids.filtered(lambda inv_line: inv_line.product_id.default_code):
            rithum_product = rithum_prod_obj.search([('product_id', '=', line.product_id.id)], limit=1)

            line_subtotal += line.price_subtotal
            line_vals = {
                "lineNumber": lineNumber,
                # "sku": line.product_id.default_code,
                "sku": rithum_product.rithum_product_id,
                "quantity": line.quantity,
                "unitPrice": line.price_unit,
                "originalOrderQuantity": line.quantity
            }
            lineNumber += 1
            lineitems.append(line_vals)

        params = {
            "invoiceId": invoice_id.name,
            "poNumber": rithum_po,
            "invoiceDate": str(invoice_id.invoice_date),
            "currencyCode": invoice_id.currency_id.name,
            "totalAmount": line_subtotal,
            "lineItemsSubtotal": line_subtotal,
            "terms": {
                "netDays": payment_term_days
            },
            "lineItems": lineitems,
            "shipFrom": {
                "firstName": shipping_from.name,
                "lastName": shipping_from.name,
                "company": sale_id.company_id.name,
                "address1": shipping_from.street,
                "address2": shipping_from.street2,
                "city": shipping_from.city,
                "region": shipping_from.state_id.name,
                "postal": shipping_from.zip,
                "country": shipping_from.country_id.code,
                "phone": shipping_from.phone,
                "email": shipping_from.email,
            },
            "shipTo": {
                "firstName": shipping_to.name,
                "company": shipping_to.name,
                "address1": shipping_to.street,
                "address2": shipping_to.street2,
                "city": shipping_to.city,
                "region": shipping_to.state_id.name,
                "postal": shipping_to.zip,
                "country": shipping_to.country_id.code,
                "phone": shipping_to.phone,
                "email": shipping_to.email,
                "name": shipping_to.display_name,
            },
            "orderType": "Dropship"
        }
        if lineitems:
            data = json.dumps(params)
            order_headers = {
                'Accept': 'application/json',
                'Content-type': 'application/json',
                'Authorization': rithum_token,
                'Content-Length': f'{len(str(data))}',
                'Host': 'api.dsco.io',
            }
            response = requests.post(rithum_invoice_url, data=data, headers=order_headers)
            response_data = response.json()
            if response.status_code == 201:
                _logger.info(f'\n---------- Invoice {invoice_id} create successfully ------------')
            else:
                error_invoice_log_obj = self.env['rithum.error.invoice.log']
                if isinstance(response_data.get('messages'), list) and 'description' in response_data.get('messages')[
                    0]:
                    error_code = response_data.get('messages')[0].get('code')
                    error_description = response_data.get('messages')[0].get('dercription')
                    description = f"""code:{error_code}\ndescription: {error_description}"""
                    _logger.error(_(f"""code:{error_code}\ndescription: {error_description}"""))
                    prepare_error_vals = {
                        'name': invoice_id.name,
                        'po_number': rithum_po,
                        'error_date': fields.date.today(),
                        'error_message': f"""code:{error_code}\ndescription: {description}""",
                        'rithum_config_id': sale_id.rithum_config_id.id
                    }
                    error_invoice_log_obj.create(prepare_error_vals)

    def action_update_product_qty(self):
        rithum_invent_product_ids = self.env['rithum.product.product'].search([('inventory_product_id.is_rithum_qty_changed', '=', True)])
        for t_con in self.search([('state', '!=', 'success'), ('active', '=', True)]):
            t_con.with_context(from_import_action=True).action_test_connection()
        for config in self.search([('state', '=', 'success'), ('active', '=', True)], limit=1):
            params = []
            rithum_inventory_update_url = config.rithum_inventory_update_url()
            rithum_token = config.rithum_auth_token()
            # for product in products:
            for rithum_product in rithum_invent_product_ids:
                product = rithum_product.inventory_product_id
                if product.default_code:
                    # add "cost": inventory_product.standard_price if client need to update product cost as well
                    stock_status = 'in-stock'
                    if product.free_qty <= 0:
                        stock_status = 'out-of-stock'

                    params.append(
                        {
                            "sku": product.default_code,
                            "quantityAvailable": product.free_qty,
                            "status": stock_status,
                            "warehouses": [
                                {
                                    "code": config.rithum_warehouse,
                                    "quantity": product.free_qty
                                }
                            ],
                        }
                    )
        data = json.dumps(params)
        order_headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json',
            'Content-type': 'application/json',
            'Authorization': rithum_token,
            'Content-Length': f'{len(str(data))}',
            'Host': 'api.dsco.io',
        }
        if params:
            response = requests.post(rithum_inventory_update_url, data=data, headers=order_headers)
            if response.status_code == 202:
                product.write({'is_rithum_qty_changed': False})
                _logger.info('\n---------- Update Inventory successfully ------------')
            else:
                inventory_error_obj = self.env['rithum.error.inventory.log']
                response_error = response.json()
                if isinstance(response_error.get('messages'), list) and 'description' in response_error.get('messages')[
                    0]:
                    error_code = response_error.get('messages')[0].get('code')
                    error_description = response_error.get('messages')[0].get('description')
                    description = f"""code:{error_code}\ndescription: {error_description}"""
                    inventory_error_obj.create({
                        'name': error_code,
                        'error_message': error_description,
                        'error_date': fields.Datetime.now(),
                        'rithum_config_id': config.id,
                    })
                    _logger.error(_(description))

    def check_rithum_order_status(self, picking_id):
        sale_id = picking_id.sale_id
        rithum_get_order_url = self.rithum_get_order_url()
        rithum_token = self.rithum_auth_token()
        order_headers = {
            'Accept': 'application/json',
            'Content-type': 'application/json',
            'Authorization': rithum_token,
        }
        params = {
            'orderKey': 'poNumber',
            'value': sale_id.customer_po
        }
        response = requests.get(rithum_get_order_url, params=params, headers=order_headers)
        if response.status_code == 200:
            response_data = response.json()
            cancel_order_warn = response_data.get('dscoStatus') if 'dscoStatus' in response_data else False
            if cancel_order_warn == 'cancelled':
                return 'cancelled', {}
            lines = response_data.get('lineItems')
            # if len(lines) != len(sale_id.order_line):
            #     return 'cancelled'
            cancelled_lines = []
            for line in lines:
                if line.get('cancelledQuantity') >= 1:
                    cancelled_lines.append(line)
            if cancelled_lines:
                return 'cancelled_line', cancelled_lines
            return False, False
        else:
            return False, False
