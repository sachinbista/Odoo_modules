# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
import requests
from odoo.exceptions import UserError
import json
import uuid

class ParcelPro():
    "Implementation of Parcelpro API"

    def __init__(self, api_key, debug_logger):
        self.env = None
        self.api_key = api_key
        self.debug_logger = debug_logger
        self.is_domestic_shipping = None
        self.context = {}

    def _make_api_auth_request(self,carier):
        """Authenticate with the ParcelPro API and obtain an authentication token."""
        url = "https://api.parcelpro.com/v2.0/auth"
        payload = {
            'username': carier.parcel_pro_username,
            'password': carier.parcel_pro_password,
            'grant_type': 'password'
        }
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            self.access_token = response.json().get('access_token')
        else:
            raise Exception("Authentication failed. Please check your credentials.")

    def ship_from_phone(self,shipper):
        if shipper.phone == True:
            numeric_digits = [char for char in shipper.phone if char.isdigit() or char.isspace()]
            cleaned_phone_number = ''.join(numeric_digits)
            return cleaned_phone_number
        else:
            return "1234567890"

    def ship_to_phone(self,recipient):
        if recipient.phone == True:
            numeric_digits = [char for char in recipient.phone if char.isdigit() or char.isspace()]
            cleaned_phone_number = ''.join(numeric_digits)
            return cleaned_phone_number
        else:
            return "1234567890"


    def ship_from(self, shipper):
        return {
                    "FirstName": shipper.firstname,
                    "LastName": shipper.lastname,
                    "StreetAddress": shipper.street,
                    "City":shipper.city,
                    "State": shipper.state_id.code,
                    "Country": shipper.country_id.code,
                    "Zip":shipper.zip,
                    "TelephoneNo": self.ship_from_phone(shipper)
        }

    def ship_to(self, recipient):
        return {
            "ContactType": recipient.id,
            "StreetAddress": recipient.street,
            "City":  recipient.city,
            "Country": recipient.country_id.code,
            "Zip": recipient.zip,
            "TelephoneNo": self.ship_to_phone(recipient)
        }

    def total_product_weight(self,order):
        total_weight = 0
        for order_line in order.order_line:
            product_weight = order_line.product_id.weight * order_line.product_uom_qty
            total_weight += product_weight
        return total_weight

    def total_product_weight_picking(self, picking):
        total_weight = 0
        for order_line in picking.move_ids:
            product_weight = order_line.product_id.weight * order_line.product_uom_qty
            total_weight += product_weight
        print("totalllweight",total_weight)
        return total_weight

    def total_product_insured_value(self,order):
        total_insured = 0
        for order_line in order.order_line:
            product_insure = order_line.product_id.insured_value
            total_insured += product_insure
        return total_insured

    def total_product_insured_value_picking(self,picking):
        total_insured = 0
        for order_line in picking.move_ids:
            product_insure = order_line.product_id.insured_value
            total_insured += product_insure
        return total_insured


    def fetch_parcelpro_carrier(self, carrier, recipient, shipper, order=False, picking=False, is_return=False):
        self._make_api_auth_request(carrier)
        if self.access_token:
            print("self.access_token",self.access_token)
            print(":::::::::::carrier",carrier)
            print("order>>>>>>>",order)
            url = "https://api.parcelpro.com/v2.0/estimator"
            if order:
                payload = {
                    "ShipToResidential": False,
                    "ShipTo": self.ship_to(recipient),
                    "ShipFrom":self.ship_from(shipper),
                    "Weight": self.total_product_weight(order),
                    "InsuredValue": self.total_product_insured_value(order),
                }
            else:
                payload = {
                    "ShipToResidential": False,
                    "ShipTo": self.ship_to(recipient),
                    "ShipFrom": self.ship_from(shipper),
                    "Weight": self.total_product_weight_picking(picking),
                    "InsuredValue": self.total_product_insured_value_picking(picking),
                }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                massage = response.json().get('Message')
                raise UserError(massage)
                return response.json().get('Message')
        else:
            return None

    def send_shipping(self, carrier, recipient, shipper, picking, is_return=False):
        self._make_api_auth_request(carrier)
        if self.access_token:
            result = self.fetch_parcelpro_carrier(carrier, recipient, shipper, picking=picking, is_return=is_return)
            print("::::>>>>>>>>>>",result)
            estimators = result.get("Estimator", [])
            global_quote_id = None
            estimator_id = None
            for estimator in estimators:
                global_quote_id = estimator.get("QuoteID")
                print("idddddddestimatord",estimator)
                estimator_id = estimator.get("EstimatorHeaderID")
            print(">>>>>>>>>>>>",global_quote_id)
            url =  f"https://api.parcelpro.com/v2.0/shipments/{global_quote_id}"
            print(">>>>token",self.access_token)
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            response = requests.post(url, headers=headers)
            print(";:::::::::::::::",response.status_code)

            if response.status_code == 200:
                # shipment_id = response.json()["shipmentId"]
                print(f"Shipment created with ID:")
            else:
                print(f"Error creating shipment:")


            # url = "https://api.parcelpro.com/v2.0/shipments/"
            # payload = {
            #     "QuoteID": 'f46d9d51-c8b9-4706-9e5e-e6c1c01c41ec',
            # }
            # headers = {
            #     'Content-Type': 'application/json',
            #     'Authorization': f'Bearer {self.access_token}'
            # }
            # response = requests.post(url, headers=headers, json=payload)
            # print("response>>>.shipping",response.text)


