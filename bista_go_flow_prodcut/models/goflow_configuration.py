# -*- coding: utf-8 -*-
import json

import requests

from odoo import models, fields


class GoFlowConfiguration(models.Model):
    _inherit = 'goflow.configuration'

    # Download Product Fields
    sync_product_url = fields.Char(string='Sync Product Data URL')
    product_import_operation = fields.Boolean(string='Sync Products')

    sync_product = fields.Boolean(string='Auto Sync Products')
    download_kit_and_group_product = fields.Boolean(string='Download Kit & Group Products')
    auto_import_product = fields.Boolean(string='Sync interval')
    auto_import_product_interval_number = fields.Integer()
    auto_import_product_interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')])
    auto_import_product_next_execution = fields.Datetime(string='Auto Next Product Execution')
    auto_import_product_user_id = fields.Many2one('res.users', string='Auto Import Product User')
    auto_map_product = fields.Boolean(string='Auto Map Product')
    map_line_ids = fields.One2many('goflow.product.map.line', 'goflow_configuration_id', string='Line')

    def _auto_goflow_download_products_data(self):
        goflow_configurration_ids = self.env['goflow.configuration'].search([])
        for each in goflow_configurration_ids:
            if each.product_import_operation:
                each.goflow_download_products_data()

    def goflow_download_products_data(self, next_filter=False):
        if next_filter:
            product_url = '/v1/products'+next_filter
        else:
            product_url = '/v1/products?filters[status]=active&sort_direction=desc&sort=id'
        config_id = self
        goflow_connection_obj = self._send_goflow_request("get", product_url, payload=False)
        goflow_products = False
        next_orders = False
        if goflow_connection_obj:
            goflow_product_json = goflow_connection_obj.json()
            goflow_products = goflow_product_json.get('data', False)
            next_orders = goflow_product_json.get("next", '')
        goflow_product_obj = self.env['goflow.product']
        for each in goflow_products:
            product_external_id = int(each.get('id', ''))
            name = each.get('details').get('name', '')
            item_number = each.get('item_number', '')
            type = each.get('type', '')
            status = each.get('status', '')
            shipping = each.get('shipping', '')
            identifiers = each.get('identifiers', '')
            goflow_product_id = (goflow_product_obj.search(
                [('product_external_id', '=', product_external_id)])) if product_external_id else False
            if goflow_product_id:
                update_values = {}
                if name and name != goflow_product_id.name:
                    update_values.update({'name': name})
                if product_external_id and product_external_id != goflow_product_id.product_external_id:
                    update_values.update({'product_external_id': product_external_id})
                if item_number and item_number != goflow_product_id.item_number:
                    update_values.update({'item_number': item_number})
                if type and type != goflow_product_id.type:
                    update_values.update({'type': type})
                if status and status != goflow_product_id.status:
                    update_values.update({'status': status})

                # updating shipping details
                if shipping['dimensions'] != None and shipping['weight'] != None:
                    weight_in_lb = shipping['weight']['amount'] / 16
                    goflow_product_id.product_id.product_length = shipping['dimensions']['length']
                    goflow_product_id.product_id.product_width = shipping['dimensions']['width']
                    goflow_product_id.product_id.product_height = shipping['dimensions']['height']
                    goflow_product_id.product_id.product_tmpl_id.weight = weight_in_lb

                records = []
                if identifiers:
                    for identifier in identifiers:
                        # try:
                        #     no_val = int(''.join(filter(str.isdigit, identifier['value'])))
                        # except Exception as e:
                        #     no_val = 1
                        # print("no_val:::::::::::::", no_val)
                        for packaging in goflow_product_id.product_id.packaging_ids:
                            if str(packaging.goflow_identifier_type) != str(identifier['type']) \
                                    and str(packaging.goflow_identifier_value) != str(identifier['value']) \
                                    and str(packaging.goflow_identifier_uom_id) != str(identifier['unit_of_measure_id']):
                                records.append((0, 0, {
                                    'name': identifier['type'],
                                    'qty': float(1),
                                    'goflow_identifier_type': identifier['type'],
                                    'goflow_identifier_value': identifier['value'],
                                    'goflow_identifier_uom_id': identifier['unit_of_measure_id'],
                                }))
                        if not goflow_product_id.product_id.packaging_ids:
                            if identifier['type'] != None:
                                records.append((0, 0, {
                                    'name': identifier['type'],
                                    'qty': float(1),
                                    'goflow_identifier_type': identifier['type'],
                                    'goflow_identifier_value': identifier['value'],
                                    'goflow_identifier_uom_id': identifier['unit_of_measure_id'],
                                }))

                    if records:
                        goflow_product_id.product_id.packaging_ids = records

                if update_values:
                    update_values.update({'data': each})
                    goflow_product_id.write(update_values)
                product_id = self.env['product.product'].search([('default_code', '=', goflow_product_id.item_number)], limit=1)
                if product_id:
                    goflow_product_id.write({'product_id': product_id.id})
            else:
                product_id = False
                if item_number:
                    product_id = self.env['product.product'].search(['|','|',('default_code', '=', item_number),('barcode', '=', item_number),('packaging_ids.name', 'in', [item_number])], limit=1)
                    if not product_id:
                        # "create product here"
                        product_id = self.create_product(each, config_id)
                    else:
                        goflow_product_obj = self.env['goflow.product']
                        goflow_product_obj.create({'product_id': product_id.id if product_id else False,
                                                   'name': each.get('name', False),
                                                   'item_number': each.get('item_number', False),
                                                   'type': 'standard',
                                                   'status': each.get('status', False),
                                                   'configuration_id': config_id.id,
                                                   'product_external_id': each.get('id', False),
                                                   'data': each})
                    # print(product_id)
        if next_orders:
            filter = next_orders.split('/v1/products')
            print("filters",filter[1])
            self.goflow_download_products_data(next_filter=filter[1])

    def create_product(self, product, config_id=None):
        product_brand_obj = self.env['product.brand']
        product_manufacturer_obj = self.env['product.manufacturer']
        country_obj = self.env['res.country']
        condition_mapping = {'New': 'new', 'Refurbished': 'refurbished', 'Unknown': 'unknown', 'Used': 'used'}
        details = product.get('details', {})
        customs = product.get('customs', {})
        brand_name = details.get('brand', False)
        manufacturer_name = details.get('manufacturer', False)
        country_name = customs.get('country_of_origin', False)
        brand = product_brand_obj.search([('name', '=', brand_name)]).id if brand_name else False
        manufacturer = product_manufacturer_obj.search(
            [('name', '=', manufacturer_name)]).id if manufacturer_name else False
        country_of_origin = country_obj.search([('code', '=', country_name.upper())]).id if country_name else False
        vals = {
            'name': details.get('name', False) or product.get('name', False),
            'default_code': product.get('item_number', False),
            'detailed_type': 'product',
            'brand': brand,
            'manufacturer': manufacturer,
            'condition': condition_mapping.get(details.get('condition', False), ''),
            'is_perishable': details.get('is_perishable', False)
        }

        if customs:
            vals.update({
                'country_of_origin': country_of_origin,
                'hs_code': customs.get('hts_tariff_code', False),
                "customs_description": customs.get('description', False)
            })

        if product.get('pricing', False):
            vals.update({'list_price': product['pricing']['default_price'],
                         'standard_price': product['pricing']['default_cost']})

        # adding shipping details
        if product.get('shipping'):
            if product.get('shipping')['dimensions'] != None:
                vals.update({
                    'product_length': product['shipping']['dimensions']['length'],
                    'product_width': product['shipping']['dimensions']['width'],
                    'product_height': product['shipping']['dimensions']['height']
                })

        # adding identifiers details
        records = []
        if product.get('identifiers') != None and product.get('identifiers'):
            for identifier in product.get('identifiers'):
                # try:
                #     no_val = int(''.join(filter(str.isdigit, identifier['value'])))
                # except Exception as e:
                #     no_val = 1
                if identifier['type'] != None:
                    records.append((0, 0, {
                        'name': identifier['type'],
                        'qty': float(1),
                        'goflow_identifier_type': identifier['type'],
                        'goflow_identifier_value': identifier['value'],
                        'goflow_identifier_uom_id': identifier['unit_of_measure_id'],
                    }))
            if records:
                vals.update({
                    'packaging_ids': records
                })

        if product.get('settings'):
            settings = product.get('settings')
            vals.update({
                'sale_ok': settings['is_sellable'],
                'purchase_ok': settings['is_purchasable']
            })
        product_id = False
        if vals['name'] != None and vals['name'] != False:
            product_id = self.env['product.product'].sudo().search([('default_code','=',product.get('item_number', False))],limit=1)
            if not product_id:
                product_id = self.env['product.product'].with_context(create_from_goflow=True).create(vals)

        # adding shipping details
        if product.get('shipping'):
            if product_id and product.get('shipping')['weight'] != None:
                weight_in_lb = product['shipping']['weight']['amount'] / 16
                product_id.product_tmpl_id.weight = weight_in_lb


        goflow_product_obj = self.env['goflow.product']
        if product_id:
            goflow_product = goflow_product_obj.create({'product_id': product_id.id if product_id else False,
                                    'name': product.get('name', False),
                                    'item_number': product.get('item_number', False),
                                    'type': product.get('type', ''),
                                    'status': product.get('status', False),
                                    'configuration_id': config_id.id,
                                    'product_external_id': product.get('id', False),
                                    'data': product})

            return goflow_product
