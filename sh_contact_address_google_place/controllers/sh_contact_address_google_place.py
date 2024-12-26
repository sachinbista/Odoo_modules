# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

import requests
from odoo import http
from odoo.http import request
from odoo.osv.expression import AND
from odoo.tools import html2plaintext

GOOGLE_MAP_PLACES = 'https://maps.googleapis.com/maps/api/place'


class CustomController(http.Controller):

    def get_google_fields_mapping(self):
        """ METHOD OF SOFTHEALER TECHNOLOGIES.

        This function returns a dictionary mapping Google Maps API fields to corresponding fields in a
        standard address format.
        :return: A dictionary mapping Google Maps API fields to corresponding fields in a local database.
        The keys in the dictionary are the local database fields, and the values are lists of possible
        Google Maps API fields that could correspond to the local field.
        """

        return {'country': ['country'],
                'street_number': ['number'],
                'administrative_area_level_3': ['city'],
                'neighborhood': [''],
                'locality': ['city'],
                'route': ['street'],
                'sublocality_level_1': ['street2'],
                'postal_code': ['zip'],
                'administrative_area_level_1': ['state', 'city'],
                'administrative_area_level_2': ['state', 'country'],
                }

    def _convert_to_standard_address(self, g_fields):
        """  METHOD OF SOFTHEALER TECHNOLOGIES.

        This function converts Google Maps API address fields to standard address fields in Odoo.

        :param g_fields: It is a list of dictionaries containing information about the address fields
        returned by the Google Maps API. Each dictionary represents a single address component, such as
        street number, city, state, etc. The dictionary contains keys such as 'long_name', 'short_name',
        and 'type', which provide information about
        :return: a dictionary containing the standard address values extracted from the input Google
        fields.
        """

        address_vals = {}
        google_fields_mapping = self.get_google_fields_mapping()
        for g_field in g_fields:
            fields_standard = google_fields_mapping[g_field['type']
                                                    ] if g_field['type'] in google_fields_mapping else []

            for s_field in fields_standard:
                if s_field in address_vals:
                    continue
                if s_field == 'country':
                    country = request.env['res.country'].search(
                        [('code', '=', g_field['short_name'].upper())], limit=1)
                    address_vals[s_field] = country.id if country else False
                    address_vals['country_code'] = country.code if country else False
                elif s_field == 'state':
                    domain = [('code', '=', g_field['short_name'].upper())]
                    if address_vals['country']:
                        domain = AND(
                            [domain, [('country_id.id', '=', address_vals['country'])]])
                    state = request.env['res.country.state'].search(domain)
                    if len(state) == 1:
                        address_vals[s_field] = state.id
                else:
                    address_vals[s_field] = g_field['long_name']
        return address_vals

    @http.route('/sh_contact_address_google_place/partial_address', type="json", auth="public", website=True)
    def sh_get_partial_address(self, partial_address):
        """ METHOD OF SOFTHEALER TECHNOLOGIES.
        This function uses the Google Places API to retrieve a list of partial addresses based on a given
        input.

        :param partial_address: `partial_address` is a string parameter that represents the partial
        address entered by the user in the frontend. This parameter is used to make a request to the
        Google Places API to get a list of suggested addresses that match the partial address entered by
        the user
        :return: A list of dictionaries containing the 'description' and 'place_id' of the partial
        address results obtained from the Google Places API. If the company is not configured with a
        valid Google API key or if there is an error during the API call, an empty list is returned.
        """

        company = request.env.user.company_id or request.env.company
        
        country_code_list = company.sh_restricted_country_ids.mapped('code')
        if country_code_list:
            result = ["country:" + str(item) + '|'  for item in country_code_list]
            test_list = [''.join(result)]

        if company and company.sh_is_enable_google_api_key and company.sh_google_api_key:
            params = {
                'key': company.sh_google_api_key,
                'fields': 'formatted_address,name',
                'inputtype': 'textquery',
                'types': 'address',
                'input': partial_address,
            }
            if country_code_list and test_list[0]:
                params.update({
                    'components': test_list[0],
                })
            try:
                results = requests.get(
                    F'{GOOGLE_MAP_PLACES}/autocomplete/json', params=params, timeout=2.5).json()
            except (TimeoutError, ValueError):
                return []
            results = results.get('predictions', []) if results.get(
                'status', False) == 'OK' else []

            return [{'description': result['description'], 'place_id': result['place_id']} for result in results]

        return []

    @http.route('/sh_contact_address_google_place/fill_address', type="json", auth="public", website=True)
    def sh_fill_address(self, address, place_id):
        """ METHOD OF SOFTHEALER TECHNOLOGIES.

        This function uses the Google Places API to fill in missing address information based on a given
        address and place ID.

        :param address: The user-inputted address that needs to be filled using the Google Places API
        :param place_id: The unique identifier for a specific place in Google Maps. It is used to
        retrieve details about the place, such as its address components and formatted address
        :return: a dictionary containing the complete address information obtained from the Google Places
        API, or an empty dictionary if the API call fails or if the website's Google Places API key is
        not set.
        """
        company = request.env.user.company_id or request.env.company
        if address and company and company.sh_is_enable_google_api_key and company.sh_google_api_key:
            params = {
                'key': company.sh_google_api_key,
                'place_id': place_id,
                'fields': 'address_component,adr_address'
            }

            try:
                results = requests.get(
                    F'{GOOGLE_MAP_PLACES}/details/json', params=params, timeout=2.5).json()

                html_address = results['result']['adr_address']
                results = results['result']['address_components']

                for res in results:
                    res['type'] = res.pop('types')[0]

            except (TimeoutError, ValueError):
                return {}

            sequence = list(self.get_google_fields_mapping().keys())
            results.sort(key=lambda result: sequence.index(
                result['type']) if result['type'] in sequence else 143)
            complete_address = self._convert_to_standard_address(results)

            # To avoid missing any type of user-inputted number
            if 'number' not in complete_address:
                house_number = address.replace(complete_address.get('zip', ''), '').replace(
                    complete_address.get('street', ''), '').replace(complete_address.get('city', ''), '').replace('-', '')
                complete_address['number'] = house_number.split(',')[0].strip()
                complete_address[
                    'formatted_street'] = f'{complete_address.get("street", "")} {complete_address["number"]}'
            else:
                html2street = html2plaintext(html_address.split(',')[0])
                street = F'{complete_address.get("street", "")} {complete_address["number"]}'
                complete_address['formatted_street'] = html2street if len(
                    html2street) >= len(street) else street
            formatted_address = {}
            if complete_address:
                state = complete_address.get('state')
                state_name = ""
                if state and complete_address.get('country_code') == 'US':
                    state_name = request.env['res.country.state'].browse(state)
                formatted_address = {
                    'country': complete_address.get('country'),
                    'country_code': complete_address.get('country_code'),
                    'city': complete_address.get('city'),
                    'formatted_street': complete_address.get('formatted_street'),
                    'street2': complete_address.get('street2'),
                    'state': state,
                    'state_name': state_name and state_name.name or '',
                    'zip': complete_address.get('zip')
                }
            return formatted_address if formatted_address else {}
        return {}


class AddressValidatorController(http.Controller):

    @http.route('/validate/address', type='json', auth='user')
    def get_redirect_model(self, address):
        return request.env['res.partner'].lookup_address(address)
