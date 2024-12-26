# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .parcel_pro_request import ParcelPro


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('parcelpro', 'Parcel Pro')
    ], ondelete={'parcelpro': lambda recs: recs.write({
        'delivery_type': 'fixed', 'fixed_price': 0,
    })})

    parcel_pro_username = fields.Char(string="User Name")
    parcel_pro_password = fields.Char(string="Password")
    parcel_pro_default_package_type_id = fields.Many2one('stock.package.type', string="Parcel Pro Package Type")

    def parcelpro_rate_shipment(self, order):
        """ Return the rates for a quotation/SO."""
        print(">>>>>>>>>>>",self._context)
        ep = ParcelPro(self.sudo().parcel_pro_username if self.prod_environment else self.sudo().parcel_pro_password,
                       self.log_xml)
        global_shipping_cost = float('inf')
        insured_value = 0
        if 'insured_value' in self._context:
            insured_value = self._context['insured_value']
            order.insured_value = insured_value
        # data = ep.fetch_parcelpro_carrier(order,insured_value)
        print("orderpartnershipping>>>",order)
        data = ep.fetch_parcelpro_carrier(self, order.partner_shipping_id, order.warehouse_id.partner_id, order)
        estimator_values = []
        if isinstance(data, dict):
            print("daaaaaaaaaaa",data)
            estimators = data.get("Estimator", [])
            for estimator in estimators:
                print("essssss",estimator)
                carrier_code = estimator.get("CarrierCode")
                shipping_cost = estimator.get("ShippingCost")
                service_code_description = estimator.get("ServiceCodeDescription")
                if shipping_cost < global_shipping_cost:
                    global_shipping_cost = shipping_cost

                if carrier_code and shipping_cost is not None:
                    existing_service = order.parcel_pro_service_ids.filtered(lambda s: s.service_code_deescription == service_code_description)
                    if existing_service:
                        existing_service.write({
                            'shipping_cost': shipping_cost,
                            'service_code_deescription': service_code_description,
                        })
                    else:
                        estimator_values.append((0, 0, {'carrier_type': carrier_code, 'shipping_cost': shipping_cost,
                                                        'service_code_deescription': service_code_description,
                                                        'carrier_product_id': self.product_id.id}))
                else:
                    raise UserError(
                        _("Carrier Code or Shipping Cost is missing"))
            order.write({'parcel_pro_service_ids': estimator_values})

        else :
            raise UserError(data)
        return {
            'success': True,
            'price': global_shipping_cost,
            'error_message': False,
            'warning_message': data.get('warning_message', False)
        }

    def parcelpro_send_shipping(self, pickings):
        ep = ParcelPro(self.sudo().parcel_pro_username if self.prod_environment else self.sudo().parcel_pro_password,
                       self.log_xml)

        # data = ep.send_shipping(pickings)
        for picking in pickings:
            result = ep.send_shipping(self, picking.partner_id, picking.picking_type_id.warehouse_id.partner_id,
                                      picking=picking)


