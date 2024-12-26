# class template for RapNet api request
# this class template is used for getting diamond prices, inventory etc information from RapNet via Rapaport.
# all the api request are handled by this class
# also this class is used for getting access token from RapNet
# will check if access token is expired or not
# if expired will get new access token
# if not expired will use existing access token

import logging
import json
import requests
from datetime import datetime, timedelta
from odoo import fields
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import date_utils

from .api_auth import BearerAuth

_logger = logging.getLogger(__name__)


class RapNetApi:
    def __init__(self, company):
        self.company = company
        self.client_id = company.client_id
        self.client_secret_key = company.client_secret_key
        self.api_host = company.api_host
        self.api_price_sheet_endpoint = company.api_price_sheet_endpoint
        self.api_filter_price_endpoint = company.api_filter_price_endpoint
        self.api_price_change_endpoint = company.api_price_change_endpoint
        self.api_access_token = company.api_access_token
        self.api_access_token_expiry = company.api_access_token_expiry
        self.api_access_token_expiry = datetime.strptime(
            self.api_access_token_expiry, DEFAULT_SERVER_DATETIME_FORMAT) if self.api_access_token_expiry else None

    def get_access_token(self):
        """
        This method is used for getting access token from RapNet
        :return: access token
        """
        try:
            url = 'https://authztoken.api.rapaport.com/api/get'
            headers = {
                'Content-type': 'application/json',
                'Accept': 'application/json'
            }
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret_key,
            }
            response = requests.post(url, data=json.dumps(data), headers=headers)
            if response.status_code == 200:
                response = response.json()
                self.api_access_token = response.get('access_token')
                self.api_access_token_expiry = fields.Datetime.now() + timedelta(seconds=response.get('expires_in'))
                return response.get('access_token')
            else:
                message_json = response.json().get('Error')
                raise UserError(f"Error Code: {message_json.get('code')} \n Error Message: {message_json.get('description')}")
        except Exception as e:
            raise UserError(e)
    
    def _get_data(self, url, params, headers={}):
        """
        This method is used for getting data from RapNet
        :param url: url of api endpoint
        :param params: json request params
        :param headers: headers to be sent
        :return: response
        """
        if self.api_access_token_expiry and self.api_access_token_expiry < datetime.now()-timedelta(seconds=120):
            self.get_access_token()
        headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                auth=BearerAuth(self.api_access_token)
            )
            if response.status_code == 200:
                return response.json()
            else:
                message_json = response.json().get('Error')
                raise UserError(f"Error Code: {message_json.get('code')} \n Error Message: {message_json.get('description')}")
        except Exception as e:
            raise UserError(e)

    def get_price_sheet(self, shape):
        """
        This method is used for getting prices from RapNet
        :param shape: shape of diamond. eg: Round/Pear.
        :return: response
        """
        try:
            url = self.api_host + self.api_price_sheet_endpoint
            request_params = {
                'shape': shape,
                'csvnormalized': True,
            }
            response = self._get_data(url, request_params)
            return response
        except Exception as e:
            raise UserError(e)
