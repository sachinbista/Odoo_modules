# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2017-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#    You should have received a copy of the License along with this program.
#    If not, see <https://store.webkul.com/license.html/>
#################################################################################

import sys
from odoo.addons.odoo_shipping_service_apps.tools import ensure_str as ES
from odoo.addons.odoo_shipping_service_apps.tools import wk_translit as WT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models
import binascii
import base64
import logging
from urllib.parse import quote_plus
_logger = logging.getLogger(__name__)
import datetime
from . import freightview_api

import requests
import json 

from odoo.http import request


class FreightviewDeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    @api.model
    def freightview_rate_shipment(self, order):
        if self.delivery_type == "freightview":
            raise UserError("Freightview Services are not available on sale order. Please confirm the sale order and choose the Carrier on Pickings")
 

    def get_freightview_items(self, pickings, currency_code=None):
        result = dict()
        packages = []
        packaging_ids = self.wk_group_by_packaging(pickings=pickings)
        total_package = 0
        for packaging_id, package_ids in packaging_ids.items():
            declared_value = sum(map(lambda i: i.cover_amount, package_ids))
            weight_value = 0
            pkg_data = packaging_id.read(['height', 'width', 'packaging_length', 'name'])[0]
            number_of_packages = len(package_ids)
            total_package += number_of_packages
            for package_id in package_ids:
                weight = round(self._get_api_weight(package_id.shipping_weight))
                weight = round(weight and weight or self.default_product_weight)
                weight_value += weight
                package_data = dict(
                    description = package_id.description,
                    weight=weight,
                    dimensions=dict(
                        length=pkg_data.get('packaging_length'),
                        width=pkg_data.get('width'),
                        height=pkg_data.get('height'),
                    )
                )
                packages.append(package_data)
                result['packages'] = packages
                result['total_package'] = total_package
                result['declared_value'] = round(declared_value)
                result['total_weight'] = round(weight_value)
                result['package'] = pkg_data.get('name')
        
        return result

    def get_origin_company(self, partner_id):
        company_name = 'NA'
        if partner_id.company_name:
            company_name = partner_id.company_name
        elif partner_id.parent_id.company_name:
            company_name = partner_id.parent_id.company_name
        elif partner_id.parent_id:
            company_name = partner_id.parent_id.name
        else:
            company_name = partner_id.name
        return company_name

    def get_freightview_request_body(self, sdk, pickings, currency_code):      
        origin_data = self.get_shipment_shipper_address(picking=pickings),
        origin_data[0].update(dict( originCompany = self.get_origin_company(pickings.picking_type_id.warehouse_id.partner_id)))
        dest_data = self.get_shipment_recipient_address(picking=pickings),
        dest_data[0].update(dict( destCompany = self.get_origin_company(pickings.partner_id)))
        items_data = self.get_freightview_items(pickings, currency_code),
        freightview_items = []
        for item in items_data[0]['packages']:
            item_dict = dict(
                description = item.get('description','NA'),
                weight = item.get('weight'),
                freightClass = self.freightClass,
                length = item['dimensions'].get('length'),
                width = item['dimensions'].get('width'),
                height = item['dimensions'].get('height'),
                package = items_data[0].get('package'),
                pieces = 1
            )
            freightview_items.append(item_dict)
        
        if origin_data[0].get('country_code') not in ["US","CA"] or  dest_data[0].get('country_code') not in ["US","CA"]:
            raise UserError("Freightview works only for USA and Canada. Either the source or the destination Country does not belong to USA or Canada!")

        freightview_request_body_data = dict(
            # pickupDate = pickings.scheduled_date,
            originCompany = origin_data[0].get('originCompany'),
            originAddress = origin_data[0].get('street'),
            originAddress2 = origin_data[0].get('street2','NA'),
            originCity = origin_data[0].get('city'),
            originState = origin_data[0].get('state_code'),
            originPostalCode = origin_data[0].get('zip'),
            originCountry = "USA" if origin_data[0].get('country_code') =="US" else "CAN",

            originType = self.freightview_origin_type,
            originContactName = origin_data[0].get('name','NA'),
            originContactPhone = origin_data[0].get('phone','NA'),   
            originContactEmail = origin_data[0].get('email','NA'),   
            originReferenceNumber = pickings.name,   
            # originInstructions
            originDockHoursOpen = "9:00 AM",
            originDockHoursClose = "5:00 PM",  

            destCompany = dest_data[0].get('destCompany'),
            destAddress = dest_data[0].get('street',),
            destAddress2 = dest_data[0].get('street2','NA'),
            destCity = dest_data[0].get('city'),
            destState = dest_data[0].get('state_code'),
            destPostalCode = dest_data[0].get('zip'),
            destCountry = "USA" if dest_data[0].get('country_code') =="US" else "CAN",
            destType = self.freightview_destination_type,
            destContactName = dest_data[0].get('name'),
            destContactPhone = dest_data[0].get('phone','NA'),
            destContactEmail = dest_data[0].get('email','NA'),
            # destReferenceNumber
            # destInstructions
            # destDockHoursOpen
            # destDockHoursClose
            billPostalCode = origin_data[0].get('zip') if origin_data[0].get('country_code') =="US" else dest_data[0].get('zip'),
            billCountry = "USA" if origin_data[0].get('country_code') =="US" else "CAN",
            # emergencyName
            # emergencyPhone
            items = freightview_items
        )
        return freightview_request_body_data
    

    def freightview_send_shipping(self, pickings):
        if pickings.freightview_activity_status == "delivered" and self._context.get("freightview_result",False):
            result = {
                    'exact_price': self._context.get("freightview_result").get("exact_price"),
                    'weight': round(float(self._context.get("freightview_result").get("exact_price"))),
                    'currency': self._context.get("freightview_result").get("currency"),
                    'date_delivery': None,
                    'tracking_number': self._context.get("freightview_result").get("shipmentDetailsUrl"),
                    'attachments': []
                }                
                
            return result
        
        
        elif pickings.freightview_activity_status == "delivered":
            freightview_shipment_result = pickings.action_get_freightview_shipping_detail()
            result = {
                    'exact_price': freightview_shipment_result.get("exact_price"),
                    'weight': round(float(freightview_shipment_result.get("exact_price"))),
                    'currency': freightview_shipment_result.get("currency"),
                    'date_delivery': None,
                    'tracking_number': freightview_shipment_result.get("shipmentDetailsUrl"),
                    'attachments': []
                }
            return result
        else:
            raise UserError('Shipping not yet confirmed by freightview!')
        

    def freightview_get_tracking_link(self, picking):
        if picking.freightview_shipmentDetailsUrl:
            return picking.freightview_shipmentDetailsUrl
        else:
            raise UserError("Tracking link not available. Please visit Freightview portal or use Freightview Shipment Details URL on picking page.")
        
    def freightview_cancel_shipment(self,pickings):
        raise ValidationError('This feature is not supported by Freightview. Please cancel the shipment from Freightview Portal.')