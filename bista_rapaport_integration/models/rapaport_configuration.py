import json
import logging
from datetime import timedelta

import requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    client_id = fields.Char(string='Client Id', help="Rapaport API Access Key")
    client_secret_key = fields.Char(
        string='Client Secret Key', help="Rapaport API Secret Key")
    api_access_token = fields.Char('API Access Token')
    api_access_token_expiry = fields.Datetime('API Access Token Expiry')
    api_host = fields.Char(string='API Host', help="Rapaport API Host",
                           default="https://technet.rapnetapis.com")
    api_price_sheet_endpoint = fields.Char(
        string='Price Sheet', help="Rapaport Price Sheet Endpoint", default="/pricelist/api/Prices/list")
    api_filter_price_endpoint = fields.Char(
        string='Filter Price', help="Rapaport Filter Price Endpoint", default="/pricelist/api/Prices")
    api_price_change_endpoint = fields.Char(
        string='Price Change', help="Rapaport Price Change Endpoint", default="/pricelist/api/Prices/changes")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    client_id = fields.Char(string='Client Id', help="Rapaport API Access Key")
    client_secret_key = fields.Char(
        string='Client Secret Key', help="Rapaport API Secret Key")
    api_host = fields.Char(string='API Host', help="Rapaport API Host")
    api_price_sheet_endpoint = fields.Char(
        string='Price Endpoint', help="Rapaport Price Endpoint")
    api_access_token = fields.Char(related='company_id.api_access_token', string='API Access Token')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.company_id.write({
            'client_id': self.client_id,
            'client_secret_key': self.client_secret_key,
            'api_host': self.api_host,
            'api_price_sheet_endpoint': self.api_price_sheet_endpoint,
        })

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        company = self.env.company
        res.update(
            client_id=company.client_id,
            client_secret_key=company.client_secret_key,
            api_host=company.api_host,
            api_price_sheet_endpoint=company.api_price_sheet_endpoint,
        )
        return res
    
    def generate_access_token(self):
        company = self.env.company
        if company.client_id and company.client_secret_key:
            try:
                access_token_endpoint = 'https://authztoken.api.rapaport.com/api/get'
                headers = {'content-type': 'application/json'}
                data = {
                    "client_id": company.client_id,
                    "client_secret": company.client_secret_key,
                }
                response = requests.post(
                    access_token_endpoint, headers=headers, data=json.dumps(data))
                response_json = response.json()
                if response.status_code == 200:
                    
                    if response_json['access_token']:
                        expiries_in = response_json['expires_in'] # in seconds
                        expiries_at = fields.Datetime.now() + timedelta(seconds=expiries_in)

                        company.write({
                            'api_access_token': response_json['access_token'],
                            'api_access_token_expiry': expiries_at
                        })
                        message_type = 'success'
                        message = 'Access Token Generated'
                else:
                    message_type = 'danger'
                    error_message_json = response_json['Error']
                    message = f"Error Code: {error_message_json['code']} \n Error Message: {error_message_json['description']}"

            except Exception as e:
                message_type = 'danger'
                message = 'Access Token Generation Failed'
                _logger.error(e)
        else:
            message_type = 'warning'
            message = 'Please enter Client Id and Secret Key'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': message_type,
                'message': _(message),
            }
        }

    