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
_logger = logging.getLogger(__name__)


from requests.auth import HTTPBasicAuth
import requests
import json

from base64 import b64encode

class FreightviewAPI:
    APIEND = dict(
        sandbox=dict(
            token = 'https://api.freightview.dev/v2.0/auth/token',
            rate_ltl='https://www.freightview.dev/api/v1.0/rates',
            rate_parcel='https://www.freightview.dev/api/v1.0/rates/parcel',
            shipment_detail='https://api.freightview.dev/v2.0/shipments',
            track_shipment = "https://api.freightview.dev/v2.0/shipments/{shipmentId}/tracking"
        ),
        production=dict(
            token = 'https://api.freightview.com/v2.0/auth/token',
            rate_ltl='https://www.freightview.com/api/v1.0/rates',
            rate_parcel='https://www.freightview.com/api/v1.0/rates/parcel',
            shipment_detail='https://api.freightview.com/v2.0/shipments',
            track_shipment = "https://api.freightview.com/v2.0/shipments/{shipmentId}/tracking"
        )
    )

    def __init__(self, *args, **kwargs):
        self.freightview_client_id = kwargs.get('freightview_client_id')
        self.freightview_client_secret = kwargs.get('freightview_client_secret')
        self.freightview_user_api_key = kwargs.get('freightview_user_api_key')
        self.freightview_account_api_key = kwargs.get('freightview_account_api_key')
        self.freightview_grant_type = kwargs.get('freightview_grant_type')
        # self.freightview_carrier_id = kwargs.get('freightview_carrier_id')
        self.freightview_enviroment = kwargs.get('freightview_enviroment')
        self.freightview_shipment_type = kwargs.get('freightview_shipment_type')

    def get_freightview_bearer_token(self):
        token_url = self.APIEND['sandbox']['token'] if self.freightview_enviroment == "test" else self.APIEND['production']['token']
        headers = {
            "content-type":"application/json",
        }
        payload = {
            "client_id" : self.freightview_client_id,
            "client_secret" : self.freightview_client_secret,
            "grant_type" : "client_credentials",
        }
        res = requests.request("POST", token_url, headers=headers, data=json.dumps(payload))
        return res.json()

    def get_freightview_auth_header(self, uname):
        token = b64encode(f"{uname}:''".encode('utf-8')).decode("ascii")
        headers = {
            'Authorization': f'Basic {token}',            
            'Content-Type': 'application/json',
            }
        return headers


    def get_freightview_query_params(self, delivery_obj, timeout):     
        carriers = ""
        for carrier in delivery_obj.freightview_carrier_ids:        
            carriers += carrier.code + ","
        return f"?timeout={timeout}&carriers={carriers[:-1]}"


    def get_freightview_book_url(self, auth_header, query_param, request_body):
        if self.freightview_shipment_type == "ltl":
            book_url = self.APIEND['sandbox']['rate_ltl'] if self.freightview_enviroment == "test" else self.APIEND['production']['rate_ltl']
        else:
            book_url = self.APIEND['sandbox']['rate_parcel'] if self.freightview_enviroment == "test" else self.APIEND['production']['rate_parcel']
        book_url +=query_param
        # _logger.info(f'----------book_url----------------{book_url}-------')
        _logger.info(f'----------data----------------{json.dumps(request_body)}-------')
        res = requests.request("POST", book_url, headers=auth_header, data=json.dumps(request_body))
        response = res.json()
        if response.get("error"):
            error = response.get("error")
            msg = response.get("message")
            raise UserError(f"Error from Freightview - {error} : {msg} ")
        
        _logger.info(f'---response----------------{response}---------------')
        bookUrl = response["links"].get("ratesUrl")
        if not bookUrl:
            raise UserError(f"Error from Freightview - Booking URL not received in response!")
        return bookUrl
        

        
    def get_freightview_shipment_details(self,shipmentId, bearer_token):
        detail_url = self.APIEND['sandbox']['shipment_detail'] if self.freightview_enviroment == "test" else self.APIEND['production']['shipment_detail']
        detail_url += "/"+str(shipmentId)
        detail_header = {'Authorization': 'Bearer ' + bearer_token}
        res = requests.get(detail_url,headers=detail_header)
        return res.json()



