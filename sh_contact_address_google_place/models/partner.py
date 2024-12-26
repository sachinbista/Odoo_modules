# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api

import requests
import re
import logging
import json

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sh_contact_google_location = fields.Char('Enter Location')

    sh_contact_place_text = fields.Char('Enter location', copy=False)
    sh_contact_place_text_main_string = fields.Char(
        'Enter location ', copy=False)
    is_address_editable = fields.Boolean('Is Address Editable')

    def write(self, values):
        result = super(ResPartner, self).write(values)
        for record in self:
            if ('street' in values or 'street2' in values or
                    'city' in values or 'state_id' in values or
                    'zip' in values or 'country_id' in values):
                record.is_address_editable = False
        return result

    def compute_address_editable(self):
        for record in self:
            record.is_address_editable = True

    @api.onchange('sh_contact_place_text_main_string')
    def onchange_technical_google_text_main_string(self):
        """to save name in google field"""
        if self.sh_contact_place_text_main_string:
            self.sh_contact_google_location = self.sh_contact_place_text_main_string

    @api.onchange('sh_contact_place_text')
    def onchange_technical_google_text(self):
        """to place info to std. address fields"""
        if self.sh_contact_place_text:
            google_place_dict = json.loads(self.sh_contact_place_text)
            if google_place_dict:
                self.zip = google_place_dict.get('zip', '')
                self.street = google_place_dict.get('formatted_street', '') or f'{google_place_dict.get("number","")} {google_place_dict.get("street","")}'
                self.street2 = google_place_dict.get('street2', '')
                self.country_code=google_place_dict.get('country_code', '')
                self.city=google_place_dict.get('city', '')
                self.country_id=google_place_dict.get('country', False)
                self.state_id=google_place_dict.get('state', False)

    def lookup_address(self, input_address):
        _logger.info(F"Formatted Address Google {input_address}")
        customer_rank = input_address.get('customer_rank') or 0
        company_id = self.env.user.company_id
        api_id = company_id.taxcloud_api_id
        api_key = company_id.taxcloud_api_key
        formatted_address = {}
        verify_address = {}
        raise_warning = False
        if input_address and company_id.allow_address_validation and customer_rank > 0:
            if input_address.get('country_code') == 'US':
                zip_match = re.match(r"^\D*(\d{5})\D*(\d{4})?", input_address.get('zip') or '')
                zips = list(zip_match.groups()) if zip_match else []
                verify_address = {
                    "Address1": input_address.get('formatted_street') or '',
                    "Address2": input_address.get('street2') or '',
                    "City": input_address.get('city') or '',
                    "State": input_address.get('state') or '',
                    "Zip5": zips.pop(0) if zips else '',
                    "Zip4": zips.pop(0) if zips else '',
                    "apiKey": api_key,
                    "apiLoginID": api_id
                }
                try:
                    resp_address_verify = self.validate_address(address=verify_address)
                    address_info = resp_address_verify.json()
                    _logger.info(F"Tax Cloud Response {address_info}")
                    state_id = False
                    if int(address_info.get('ErrNumber', False)):
                        pass
                    else:
                        if address_info.get('State'):
                            state_id = self.env['res.country.state'].search([
                                ('code', '=', address_info.get('State')),
                                ('country_id.code', '=', input_address.get('country_code'))])
                        formatted_address = {
                            'country': input_address.get('country'),
                            'country_code': input_address.get('country_code'),
                            'city': address_info.get('City'),
                            'formatted_street': address_info.get('Address1'),
                            'street2': input_address.get('street2'),
                            'state': state_id and state_id.id or False,
                            'state_name': state_id and state_id.name or False,
                            'zip': address_info.get('Zip5')
                        }
                        _logger.info(F"Formatted Address Tax Cloud {formatted_address}")
                except Exception as ex:
                    _logger.info(ex)
                    raise_warning = True
        if verify_address and formatted_address:
            if input_address.get('formatted_street') != formatted_address['formatted_street']:
                raise_warning = True
            if input_address.get('city') != formatted_address['city']:
                raise_warning = True
            if input_address.get('state') != formatted_address['state']:
                raise_warning = True
            if input_address.get('zip') != formatted_address['zip']:
                raise_warning = True
        if raise_warning:
            return formatted_address
        else:
            return False

    def validate_address(self, address={}):
        resp_address_verify = {}
        if address:
            resp_address_verify = requests.post(
                "https://api.taxcloud.net/1.0/TaxCloud/VerifyAddress",
                json=address)
        return resp_address_verify
