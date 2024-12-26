# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GoFlowProduct(models.Model):
    _name = 'goflow.product'
    _description = 'GoFlow Product'

    name = fields.Char(string='GoFlow Product Name')
    item_number = fields.Char(string='GoFlow Product Item No')
    product_external_id = fields.Integer(string='GoFlow Product ID')
    product_id = fields.Many2one('product.product', string='Product')
    type = fields.Selection([
        ('group', 'Group'),
        ('kit', 'Kit'),
        ('standard', 'Standard')], string='Product Type')
    configuration_id = fields.Many2one('goflow.configuration', string='Instance')
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')], string='Status')
    data = fields.Text(string='GoFlow Product Data')
    info = fields.Text(string='GoFlow Product Info')
    create_update_in_goflow = fields.Boolean(string='To be Created/Updated In Goflow')
    create_update_in_odoo = fields.Boolean(string='To be Created/Updated In Odoo')

#
#     def import_goflow_product(self, go_flow_instance, product):
#         print("\n\n Order", product, go_flow_instance)
#         response_get_product = go_flow_instance._send_get_request('v1/product/' + str(product.id))
#         if response_get_product != 200:
#             payload = {
#                 "type": "standard",
#                 "item_number": product.id,
#                 "details": {
#                     "name": product.name,
#                     "description": product.name,
#                 },
#                 "pricing": {
#                     "default_cost": 0.01,
#                     "default_price": 0.01,
#                     "msrp": 0.01,
#                     "map": 0.01
#                 },
#                 "settings": {
#                     "fulfillment_method": "warehouse",
#                     "is_purchasable": True,
#                     "is_sellable": True
#                 },
#                 "units_of_measure": {
#                     "all": [
#                         {
#                             "quantity": 2,
#                             "abbreviation": "string",
#                             "description": "string"
#                         }
#                     ],
#                     "defaults": {
#                         "purchasing": "string",
#                         "sales": "string",
#                         "shipping": "string"
#                     }
#                 },
#                 "identifiers": [
#                     {
#                         "type": "string",
#                         "value": "string",
#                         "unit_of_measure_abbreviation": "string"
#                     }
#                 ],
#                 "shipping": {
#                     "weight": {
#                         "measure": "pounds",
#                         "amount": 0.001
#                     },
#                     "dimensions": {
#                         "measure": "inches",
#                         "length": 0.001,
#                         "width": 0.001,
#                         "height": 0.001
#                     },
#                     "insured_value": 0.01
#                 },
#                 "customs": {
#                     "description": "string",
#                     "declared_value": 0.01,
#                     "hts_tariff_code": "string"
#                 }
#             }
#
#             response_create_product = go_flow_instance._send_post_request('v1/products/', payload)
#             print("response_create_product", response_create_product)


# def create(self, vals):
#   res = super()
#   if config_id.sync_product:
#     res.go_flow_product_sync(config_id)
#
#
#
# def write(self, vals):
#   res = super()
#   if config_id.sync_product:
#     res.go_flow_product_sync(config_id)
#
#
# def go_flow_product_sync(self, config_id):
#     payload =self.go_flow_product_data(payload=False)
#     product_response = config_id._send_goflow_request('post','v1/product',payload)
#     if product_response == 200:
#       self.odoo_create_go_flow_product(product_id, product_response)
#
#
# def go_flow_product_data(self, payload):
#    odoo_goflow_id =  self.env['goflow.product'].search([('product_id','=',123)])
#   if not odoo_goflow_id:
#       payload.update{
#       'prpd':,
#       'type':
#       }
#
#       return payload
#   go_flow_product_response = config_id._send_goflow_request('get','v1/product/{goflowproduct_id}',payload)
#   if go_flow_product_response == 200:
#       "code here "
#
# def odoo_create_go_flow_product(product_id, product_response):
#     """
#        create a goflow product inside a catalog
#      """
