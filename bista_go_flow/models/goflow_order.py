# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError, ValidationError
import json
import logging
_logger = logging.getLogger(__name__)


class GoFlowOrder(models.Model):
    _name = 'goflow.order'
    # _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Goflow Order Downloaded Data'
    _rec_name = 'order_number'

    goflow_order_status = fields.Char(string='Goflow Order Status')
    order_number = fields.Char(string='Goflow Order No')
    instance_id = fields.Many2one(comodel_name='goflow.configuration', string='Instance')
    goflow_order_id = fields.Integer(string='Goflow Order ID')
    status = fields.Selection([('unprocessed', 'Unprocessed'), ('in_process', 'In Process'),
                               ('done', 'Processed'), ('error', 'Error')], string='Import Status')
    order_data = fields.Text(string='JSON OrderData')
    order_date = fields.Datetime(string='Order Date')
    sale_order_id = fields.Many2one('sale.order')
    check_order_status = fields.Boolean(string='Check Order')

    
    def sync_go_flow_order(self,filter=None):
        _logger.info("sync_go_flow_order::::::::::::::::::")
        go_flow_instance = self.env['goflow.configuration'].search(
            [('active', '=', True), ('state', '=', 'done'), ('sale_order_import_operation', '=', True)])
        goflow_order_obj = self.env['goflow.order']
        if go_flow_instance:
            try:
                if filter == None:
                    # last_fetch_order = goflow_order_obj.search([],order='goflow_order_id desc', limit=1)
                    # _logger.info("\nlast_fetch_order:::::::::::::::::: %s" % last_fetch_order, last_fetch_order.goflow_order_id)
                    # if last_fetch_order:
                    #     last_fetch_order_data = eval(last_fetch_order.order_data)
                    #     _logger.info("\nlast_fetch_order_data:::::::::::::::::: %s" % last_fetch_order_data)

                    #     if len(last_fetch_order_data.get('date')) >= 21:
                    #         dt_object = datetime.strptime(last_fetch_order_data.get('date'), '%Y-%m-%dT%H:%M:%S.%fZ')
                    #         zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                    #         zero_time_str = zero_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    #     else:
                    #         dt_object = datetime.strptime(last_fetch_order_data.get('date'), '%Y-%m-%dT%H:%M:%SZ')
                    #         zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                    #         zero_time_str = zero_time.strftime('%Y-%m-%dT%H:%M:%SZ')

                    #     # Set time component to midnight (zero time)
                    #     zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)

                    if go_flow_instance.goflow_sync_date:
                        sync_date = go_flow_instance.convert_odoo_date_to_goflow_format(go_flow_instance.goflow_sync_date)
                    else:
                        sync_date = go_flow_instance.convert_odoo_date_to_goflow_format(datetime.now())
                    if sync_date:
                        if len(sync_date) >= 21:
                            dt_object = datetime.strptime(sync_date, '%Y-%m-%dT%H:%M:%S.%fZ')
                            zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                            zero_time_str = zero_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        else:
                            dt_object = datetime.strptime(sync_date, '%Y-%m-%dT%H:%M:%SZ')
                            zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                            zero_time_str = zero_time.strftime('%Y-%m-%dT%H:%M:%SZ')

                        # Set time component to midnight (zero time)
                        zero_time = zero_time_str

                        url = f"/v1/orders?sort=id&sort_direction=asc&filters[status:not]=canceled&filters[date:gte]={zero_time}"
                else:
                    url = '/v1/orders' + filter
                goflow_order_response = go_flow_instance._send_goflow_request('get', url)
                _logger.info("goflow fetch order with url %s and respose data %s and time" % (url,goflow_order_response))
                if goflow_order_response:
                    goflow_order_response = goflow_order_response.json()
                    orders = goflow_order_response.get("data", [])
                    next_orders = goflow_order_response.get("next", '')
                    if orders:
                        for order in orders:
                            exist_order = goflow_order_obj.search([('goflow_order_id','=',order['id'])])
                            if not exist_order:
                                self.create_goflow_order(order,go_flow_instance)
                            else:
                                self.status_and_future_dated_order_update(order,go_flow_instance,exist_order.sale_order_id)



                    else:
                        _logger.info("No Orders found.")

                    if next_orders:
                        filter = next_orders.split('v1/orders')
                        # go_flow_instance.sync_sale_order_filter = filter[1]
                        goflow_order_obj.sync_go_flow_order(filter=filter[1])
                else:
                    _logger.info(f"Failed to retrieve orders. Status code: {goflow_order_response}")
            except Exception as e:
                _logger.info(f"An error occurred: {e}")


    def create_goflow_order(self, order,go_flow_instance):
        vals ={}
        if order['billing_address']:
            
            order_line = self.prepare_order_vals(order,go_flow_instance)
            order_date = go_flow_instance.convert_goflow_date_to_odoo_format(order['date'])
            delivery_date = ''
            commitment_date = ''
            if order['ship_dates']['earliest_ship'] != None:
                delivery_date = order['ship_dates']['earliest_ship']
            elif order['ship_dates']['latest_ship'] != None:
                delivery_date = order['ship_dates']['latest_ship']
            if order['status'] == 'future_dated':
                if delivery_date:
                    commitment_date = go_flow_instance.convert_goflow_date_to_odoo_format(delivery_date)
                    future_date_minus_days = int(self.env['ir.config_parameter'].get_param('goflow_future_date_minus_days', 0))
                    commitment_date = commitment_date - timedelta(future_date_minus_days)
            else:
                if order['shipment']['shipped_at'] != None:
                    commitment_date = go_flow_instance.convert_goflow_date_to_odoo_format(order['shipment']['shipped_at'])

            goflow_store_id = self.env['goflow.store'].search([('store_id','=',order['store']['id'])], limit=1)
            if not goflow_store_id:
                goflow_store_id = self._create_store(order['store'])
            
            if goflow_store_id.partner_id:
                partner_id = goflow_store_id.partner_id
            else:
                partner_id = self.check_goflow_customer(order['billing_address'],order['shipping_address'],go_flow_instance)
            
            company_id = self.env['res.company'].sudo().search([('goflow_store_ids','in',goflow_store_id.id)], limit=1)
            if not company_id:
                company_id = self.env.ref('base.main_company')
            
            goflow_warehouse = self.env['goflow.warehouse'].search([
                ('goflow_warehouse_id','=',order['warehouse']['id']),
                ('company_id','=',company_id.id)
            ])
            if goflow_warehouse:
                warehouse = goflow_warehouse.warehouse_id.id
            else:
                warehouse_id = self.env['stock.warehouse'].sudo().search([('is_default_warehouse','=',True),('company_id','=',company_id.id)], limit=1)
                if not warehouse_id:
                    warehouse_id = self.env['stock.warehouse'].sudo().search([('company_id','=',company_id.id)], limit=1, order='id asc')
                warehouse = warehouse_id.id
            
            sale_order_id = self.env['sale.order'].with_user(company_id.goflow_api_user.id).create({
                'company_id' : company_id.id,
                'partner_id' : partner_id.id,
                'date_order' : order_date,
                'goflow_order_date' : order_date,
                'user_id' : company_id.goflow_api_user.id, #self.env.user.id
                'warehouse_id' : warehouse,
                'goflow_store_id' : goflow_store_id.id,
                'external_origin' : 'go_flow',
                'order_line':  order_line,
                'commitment_date': commitment_date if commitment_date else order_date,
                'goflow_order_status': order['status'],
                'goflow_warehouse': order['warehouse']['name'] if 'warehouse' in order else '',
                'goflow_order_no': order['order_number']
            })

            # save shipping address details
            if sale_order_id:
                self._set_shipping_details(order['shipping_address'],sale_order_id)

            # save shipment details
            if sale_order_id:
                self._set_shipment_details(order['shipment'],sale_order_id)
            
            # save currency_code for shipment 
            if order['summary']:
                sale_order_id.sudo().goflow_currency_code = order['summary']['total']['currency']['code'] if order['summary']['total']['currency']['code'] else ''
                goflow_currency_code = sale_order_id.sudo().goflow_currency_code
                odoo_currency = self.env['res.currency'].search([('name','=',goflow_currency_code.upper())])
                if odoo_currency:
                    price_list = self.env['product.pricelist'].search([('currency_id','=',odoo_currency.id)],limit=1)
                    if price_list:
                        sale_order_id.sudo().pricelist_id = price_list.id
                    sale_order_id.sudo().currency_id = odoo_currency.id

            goflow_order_id = self.create({
                'goflow_order_id' : order['id'],
                'order_number' : order['order_number'],
                'goflow_order_status' : order['status'],
                'instance_id': go_flow_instance.id,
                'status' : 'done',
                'order_data': order,
                'sale_order_id' : sale_order_id.id if sale_order_id else False,
            })

            # confirming sale order if customer match with configuration customer list
            # customer_ids = company_id.goflow_customer_ids
            # if sale_order_id.partner_id.id in customer_ids.ids:
            #     sale_order_id.action_confirm()

            if sale_order_id and goflow_order_id:
                sale_order_id.sudo().origin = goflow_order_id.goflow_order_id
                sale_order_id.sudo().name = sale_order_id.sudo().name + "-" + str(goflow_order_id.order_number)

            # auto confirm all goflow orders except review orders
            goflow_orders = self.env['goflow.order'].search([('order_number','=',goflow_order_id.order_number)])
            if len(goflow_orders) == 1:
                goflow_review_order_ids = company_id.goflow_review_order_ids
                if sale_order_id.goflow_store_id.id not in goflow_review_order_ids.ids:
                    if len(sale_order_id.sudo().order_line) > 0:
                        sale_order_id.sudo().action_confirm()



    def _set_shipping_details(self,shipping_address,sale_order_id):
        # shipping details
        if shipping_address['first_name'] != None or shipping_address['last_name'] != None:
            if shipping_address['first_name'] != None:
                sale_order_id.sudo().goflow_customer_name = shipping_address['first_name']
            if shipping_address['last_name'] != None:
                sale_order_id.sudo().goflow_customer_name += " " + shipping_address['last_name']
        if shipping_address['company']:
            sale_order_id.sudo().goflow_company = shipping_address['company']
        if shipping_address['street1']:
            sale_order_id.sudo().goflow_street1 = shipping_address['street1']
        if shipping_address['street2']:
            sale_order_id.sudo().goflow_street2 = shipping_address['street2']
        if shipping_address['city']:
            sale_order_id.sudo().goflow_city = shipping_address['city']
        if shipping_address['state']:
            sale_order_id.sudo().goflow_state = shipping_address['state']
        if shipping_address['zip_code']:
            sale_order_id.sudo().goflow_zip_code = shipping_address['zip_code']
        if shipping_address['country_code']:
            sale_order_id.sudo().goflow_country_code = shipping_address['country_code']
        if shipping_address['email']:
            sale_order_id.sudo().goflow_email = shipping_address['email']
        if shipping_address['phone']:
            sale_order_id.sudo().goflow_phone = shipping_address['phone']

    def _set_shipment_details(self,shipment,sale_order_id):
        if shipment['type']:
            sale_order_id.sudo().goflow_shipment_type = shipment['type']
        if shipment['carrier'] and shipment['carrier'] != "unknown":
            sale_order_id.sudo().goflow_carrier = shipment['carrier']
        if shipment['shipping_method'] and shipment['shipping_method'] != "unknown":
            sale_order_id.sudo().goflow_shipping_method = shipment['shipping_method']
        if shipment['scac']:
            sale_order_id.sudo().goflow_scac = shipment['scac']
        if shipment['shipped_at']:
            sale_order_id.sudo().goflow_shipped_at = shipment['shipped_at']

    def _create_store(self,store):
        goflow_store_id = self.env["goflow.store"].create({
            'store_id' : store['id'],
            'name' : store['name'],
            'channel' : store['channel'],
        })
        return goflow_store_id

    def prepare_order_vals(self,order,go_flow_instance):
        # company_id = self.env.user.company_id
        records= []
        line_shipping_charge = 0
        for line in order['lines']:
            if line['product'] != None:
                price_unit = 0
                price_unit_disc = 0
                discount_percentage = 0
                line_quantity = line['quantity']['amount'] if line['quantity']['amount'] else 0
                currency_id = False
                for charges in line['charges']:
                    if charges['type'] == 'price':
                        price_unit = charges['amount']
                        price_unit_disc = charges['amount'] * line_quantity

                        goflow_currency_code = charges['currency']['code'] if charges['currency']['code'] else None
                        if goflow_currency_code:
                            odoo_currency = self.env['res.currency'].search([('name', '=', goflow_currency_code.upper())])
                            if odoo_currency:
                                currency_id = odoo_currency.id

                    elif charges['type'] == 'discount':
                        if price_unit:
                            discount_amount = charges['amount']
                            discount_percentage = round(((abs(discount_amount) * 100)/price_unit_disc),2)
                    elif charges['type'] == 'shipping':
                        line_shipping_charge += charges['amount']
                goflow_product = self.env['goflow.product'].search([('product_external_id','=',line['product']['id'])])
                if not goflow_product:
                    goflow_product = go_flow_instance.create_product(line['product'],go_flow_instance)
                if goflow_product:
                    records.append((0, 0, {
                        'product_id': goflow_product.product_id.id,
                        'name': goflow_product.product_id.name,
                        # 'company_id' : company_id.id,
                        'product_uom_qty': line['quantity']['amount'] if line['quantity']['amount'] else 0,
                        'product_uom': goflow_product.product_id.uom_id.id,
                        'price_unit': price_unit,
                        'discount': discount_percentage,
                        'goflow_order_line_id': line['id'],
                        'currency_id': currency_id
                    }))

        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        line_shipping_added = False
        for charge in order['charges']:
            if charge['type'] == 'discount':
                discount_product_id = int(IrConfigParameter.get_param("bista_go_flow.discount_product")) or False
                discount_product = self.env['product.product'].browse(discount_product_id)
                if discount_product:
                    amount = charge['amount']
                    records.append((0, 0, {
                        'product_id': discount_product.id,
                        'name': discount_product.name,
                        # 'company_id' : company_id.id,
                        'product_uom_qty': 1,
                        'product_uom': discount_product.uom_id.id,
                        'price_unit': amount
                    }))
            if charge['type'] == 'shipping':
                shipping_product_id = int(IrConfigParameter.get_param("bista_go_flow.shipping_product")) or False
                shipping_product = self.env['product.product'].browse(shipping_product_id)
                if shipping_product:
                    amount = charge['amount']
                    records.append((0, 0, {
                        'product_id': shipping_product.id,
                        'name': shipping_product.name,
                        # 'company_id' : company_id.id,
                        'product_uom_qty': 1,
                        'product_uom': shipping_product.uom_id.id,
                        'price_unit': amount + line_shipping_charge
                    }))
                    line_shipping_added = True
            elif line_shipping_charge:
                shipping_product_id = int(IrConfigParameter.get_param("bista_go_flow.shipping_product")) or False
                shipping_product = self.env['product.product'].browse(shipping_product_id)
                if shipping_product:
                    records.append((0, 0, {
                        'product_id': shipping_product.id,
                        'name': shipping_product.name,
                        # 'company_id' : company_id.id,
                        'product_uom_qty': 1,
                        'product_uom': shipping_product.uom_id.id,
                        'price_unit': line_shipping_charge
                    }))
                    line_shipping_added = True
        else:
            if line_shipping_charge and not line_shipping_added:
                shipping_product_id = int(IrConfigParameter.get_param("bista_go_flow.shipping_product")) or False
                shipping_product = self.env['product.product'].browse(shipping_product_id)
                if shipping_product:
                    records.append((0, 0, {
                        'product_id': shipping_product.id,
                        'name': shipping_product.name,
                        # 'company_id' : company_id.id,
                        'product_uom_qty': 1,
                        'product_uom': shipping_product.uom_id.id,
                        'price_unit': line_shipping_charge
                    }))


        return records

    def check_goflow_customer(self,billing_address,shipping_address,go_flow_instance):
        fullname = ''
        if billing_address['company'] != None:
            customer_name = billing_address['company']
            fullname = customer_name.strip()
        elif billing_address['first_name'] != None and billing_address['last_name'] != None:
            fullname = billing_address['first_name'] + " " + billing_address['last_name']
        domain = []
        if fullname:
            domain.append(('name','=',fullname))
        email = False
        if billing_address['email'] != None:
            email = billing_address['email']
        if email:
            domain.append(('email','=',email))
        existing_partner_id = False
        if email:
            existing_partner_id = self.env['res.partner'].sudo().search(domain, limit=1)
        else:
            existing_partner_id = self.env['res.partner'].sudo().search(domain, limit=1)
        if not existing_partner_id:
            partner_values = {
                'name': fullname,
                'email': email or "",
                'active': True,
                'currency_id': False,
                'customer_rank': 1,
            }
            partner_id = go_flow_instance.with_context({'is_contact':True}).create_partner(partner_values,billing_address,shipping_address)
            return partner_id
        return existing_partner_id

    def get_bulk_sale_order(self):        
        go_flow_instance = self.env['goflow.configuration'].search(
            [('active', '=', True), ('state', '=', 'done'), ('sale_order_import_operation', '=', True)])

        default_filter = '?filters[status]=ready_to_pick'
        if go_flow_instance.sync_sale_order_filter:
            default_filter = go_flow_instance.sync_sale_order_filter
        goflow_order_obj = self.env['goflow.order']
        try:
            goflow_order_response = go_flow_instance._send_goflow_request('get', "/v1/orders" + default_filter)
            if goflow_order_response:
                goflow_order_response = goflow_order_response.json()
                orders = goflow_order_response.get("data", [])
                next_orders = goflow_order_response.get("next", '')

                if orders:
                    for order in orders:
                        exist_order = goflow_order_obj.search([('goflow_order_id','=',order['id'])])
                        if not exist_order:
                            self.create_goflow_order(order,go_flow_instance)
                        else:
                            self.status_and_future_dated_order_update(order, go_flow_instance, exist_order.sale_order_id)

                if next_orders:
                    filter = next_orders.split('v1/orders')
                    # go_flow_instance.sync_sale_order_filter = filter[1]
                    goflow_order_obj.get_bulk_sale_order()


                else:
                    print("No  Orders found.")
            else:
                print(f"Failed to retrieve orders. Status code: {response.status_code}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def goflow_set_order_hold(self):
        # set odoo sale order on hold
        self.sudo().sale_order_id.state = 'hold'

        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        url = f"/v1/orders/{self.goflow_order_id}/holds"
        if go_flow_instance_obj:
            response = go_flow_instance_obj._send_goflow_request('post', url)
            if response.status_code == 204:
                self.sudo().sale_order_id.message_post(body="Goflow Order Successfully set on Hold")
            else:
                self.sudo().sale_order_id.message_post(body="Goflow Order Failed to set on Hold")

    def goflow_unhold_order(self):
        # set odoo sale order unhold
        self.sale_order_id.state = 'draft'

        go_flow_instance_obj = self.env['goflow.configuration'].search([('active', '=', True), ('state', '=', 'done')], limit=1)
        url = f"/v1/orders/{self.goflow_order_id}/holds"
        if go_flow_instance_obj:
            response = go_flow_instance_obj._send_goflow_request('delete', url)
            if response.status_code == 204:
                self.sale_order_id.message_post(body="Goflow Order Successfully Unhold")
            else:
                self.sale_order_id.message_post(body="Goflow Order Failed to Unhold")

    def update_gflow_shipping_details(self):
        for rec in self:
            data = eval(rec.order_data)
            shipment = data['shipment']
            rec.sale_order_id.sudo().goflow_shipment_type = shipment['type']
            rec.sale_order_id.sudo().goflow_carrier = shipment['carrier']
            rec.sale_order_id.sudo().goflow_shipping_method = shipment['shipping_method']
            rec.sale_order_id.sudo().goflow_scac = shipment['scac']
            rec.sale_order_id.sudo().goflow_shipped_at = shipment['shipped_at']

    def status_and_future_dated_order_update(self, order,go_flow_instance,odoo_order):
        vals ={}
        if order['billing_address']:
            delivery_date = ''
            commitment_date = ''
            if order['ship_dates']['earliest_ship'] != None:
                delivery_date = order['ship_dates']['earliest_ship']
            elif order['ship_dates']['latest_ship'] != None:
                delivery_date = order['ship_dates']['latest_ship']
            if order['status'] == 'future_dated':
                if delivery_date:
                    commitment_date = go_flow_instance.convert_goflow_date_to_odoo_format(delivery_date)
                    future_date_minus_days = int(self.env['ir.config_parameter'].sudo().get_param('goflow_future_date_minus_days', 0))
                    commitment_date = commitment_date - timedelta(future_date_minus_days)

                if commitment_date:
                    order_pickings = odoo_order.sudo().picking_ids.filtered(lambda a:a.state not in ['done','cancel'])
                    total_pickings = order_pickings + self.env['stock.picking'].sudo().search([('intercom_sale_order_id','=',odoo_order.id),('state','not in',['done','cancel'])])
                    odoo_order.sudo().write({'commitment_date': commitment_date, 'goflow_order_status': order['status']})
                    total_pickings.sudo().write({'scheduled_date': commitment_date})
            else:
                # commitment_date = go_flow_instance.convert_goflow_date_to_odoo_format(delivery_date)
                odoo_order.sudo().write({'goflow_order_status': order['status']})
                if order['status'] == 'on_hold':
                    odoo_order.sudo().write({'goflow_order_status': order['status'],'state': 'hold'})
                if order['status'] == 'need_to_review':
                    odoo_order.sudo().write({'goflow_order_status': order['status'], 'state': 'need_to_review'})
                else:
                    odoo_order.sudo().write({'goflow_order_status': order['status']})


    def sync_split_go_flow_order(self,filter=None):
        go_flow_instance = self.env['goflow.configuration'].search(
            [('active', '=', True), ('state', '=', 'done'), ('sale_order_import_operation', '=', True)])
        goflow_order_obj = self.env['goflow.order']
        if go_flow_instance:
            try:
                if go_flow_instance.goflow_pick_date:
                    sync_date = go_flow_instance.convert_odoo_date_to_goflow_format(go_flow_instance.goflow_pick_date)

                    if sync_date:
                        if len(sync_date) >= 21:
                            dt_object = datetime.strptime(sync_date, '%Y-%m-%dT%H:%M:%S.%fZ')
                            zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                            zero_time_str = zero_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                        else:
                            dt_object = datetime.strptime(sync_date, '%Y-%m-%dT%H:%M:%SZ')
                            zero_time = dt_object.replace(hour=0, minute=0, second=0, microsecond=0)
                            zero_time_str = zero_time.strftime('%Y-%m-%dT%H:%M:%SZ')

                        # Set time component to midnight (zero time)
                        zero_time = zero_time_str

                    if filter == None:
                        url = f"/v1/orders?sort=id&sort_direction=asc&filters[status:not]=canceled&filters[status:not]=shipped&filters[date:gte]={zero_time}"
                    else:
                        url = '/v1/orders' + filter
                    goflow_order_response = go_flow_instance._send_goflow_request('get', url)
                    if goflow_order_response:
                        goflow_order_response = goflow_order_response.json()
                        orders = goflow_order_response.get("data", [])
                        next_orders = goflow_order_response.get("next", '')
                        if orders:
                            for order in orders:
                                goflow_pick_date = datetime.now() - timedelta(hours=5, minutes=0)
                                exist_order = goflow_order_obj.search([('goflow_order_id','=',order['id']),('order_number','=',order['order_number'])], limit=1)
                                if exist_order:
                                    pass
                                else:
                                    split_orders = goflow_order_obj.search([('goflow_order_id','!=',order['id']),('order_number','=',order['order_number'])], limit=1)

                                    if split_orders:
                                        if split_orders.sale_order_id.goflow_order_date <= goflow_pick_date:
                                            # cancel order old/main order
                                            split_orders.sale_order_id._action_cancel()
                                            split_orders.sale_order_id.stock_transfer_id.action_cancel()

                                        self.create_goflow_order(order,go_flow_instance)

                            if next_orders:
                                filter = next_orders.split('v1/orders')
                                goflow_order_obj.sync_split_go_flow_order(filter=filter[1])
            except Exception as e:
                _logger.info(f"An error occurred: {e}")

    def get_goflow_order_data_in_json(self):
        order_data = eval(self.order_data)
        return order_data

class GoFlowStore(models.Model):
    _name = 'goflow.store'
    _description = 'Goflow Store Downloaded Data'

    name = fields.Char()
    store_id = fields.Integer()
    channel = fields.Char()
    partner_id = fields.Many2one("res.partner")
    require_manual_shipment = fields.Boolean()