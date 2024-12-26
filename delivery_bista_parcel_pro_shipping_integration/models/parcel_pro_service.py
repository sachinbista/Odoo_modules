# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models, _


class ParcelProService(models.Model):
    _name = 'parcelpro.service'
    _description = 'Parcel Pro Service'


    parcel_pro_service_id = fields.Many2one('sale.order',String="Parcel Pro")
    carrier_type = fields.Char(string="Carrier")
    shipping_cost = fields.Float(string="Shipping Cost")
    service_code_deescription = fields.Char(string="Service Description")
    add_shipping = fields.Boolean("Service Availability",default=True)
    carrier_product_id = fields.Many2one('product.product')

    def select_shipping_method(self):
        for parcel_pro_service in self:
            sale_order_id = parcel_pro_service.parcel_pro_service_id
            product_id = parcel_pro_service.carrier_product_id.id
            existing_order_line = sale_order_id.order_line.filtered(lambda line: line.product_id.id == product_id)
            if existing_order_line:
                existing_order_line.write({
                    'product_uom_qty': 1,
                    'price_unit': parcel_pro_service.shipping_cost,
                    'name': parcel_pro_service.service_code_deescription,
                    'price_subtotal': parcel_pro_service.shipping_cost,
                })
            else:
                order_line_values = {
                    'order_id': sale_order_id.id,
                    'product_template_id': product_id,
                    'product_id': product_id,
                    'name': parcel_pro_service.service_code_deescription,
                    'product_uom_qty': 1,
                    'price_unit': parcel_pro_service.shipping_cost,
                    'price_subtotal': parcel_pro_service.shipping_cost,
                }
                sale_order_id.order_line.create(order_line_values)


