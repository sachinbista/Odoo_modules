import logging
import requests
import json
from odoo import fields, models, api
from odoo.tools.misc import format_date, parse_date
from ..tools.api_auth import BearerAuth
from ..tools.rapaport_api_request import RapNetApi

_logger = logging.getLogger(__name__)


class RapaportAPIPrice(models.Model):
    _name = 'rapaport.api.price'
    _description = 'Rapaport API Price Sheet'
    _rec_name = 'name'

    name = fields.Char(string='Name')
    unique_id = fields.Char(string='Unique Id', index=True,
                            copy=False, compute='_compute_unique_id', store=True)
    shape = fields.Char(string='Shape', required=True)
    low_size = fields.Float(string='Low Size')
    high_size = fields.Float(string='High Size')
    color = fields.Char(string='Color', required=True)
    clarity = fields.Char(string='Clarity', required=True)
    caratprice = fields.Float(string='Carat Price')
    date = fields.Date(string='Date')
    old_caratprice = fields.Float(string='Old Carat Price')
    old_date = fields.Date(string='Old Date')

    sql_constraints = [
        ('code_unique_id_uniq', 'unique (unique_id)',
         'The unique_id of the price must be!')
    ]

    def _return_unique_id(self, shape, color, clarity):
        unique_id = "%s-%s-%s" % (shape, color, clarity)
        return unique_id.lower()

    def _return_name(self, shape, color, clarity):
        name = f"{shape}-{color}-{clarity}"
        return name

    @api.depends('shape', 'color', 'clarity')
    def _compute_unique_id(self):
        for record in self:
            record.unique_id = self._return_unique_id(
                record.shape, record.color, record.clarity)
            record.name = self._return_name(
                record.shape, record.color, record.clarity)

    @api.model
    def get_price_from_api(self):
        _logger.info("Get Price From API")
        company = self.env.company
        rapnet_api = RapNetApi(company)
        # get_price_endpoint = company.api_host + company.api_price_sheet_endpoint
        response_datas = []

        # headers = {'content-type': 'application/json'}
        # access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik16aERRMFExTURFeVJqSTNRa0k0TTBGRVJUZzFNekUzTWtOQ09UTXhNREZDTVVZM1JURkNNZyJ9.eyJodHRwOi8vcmFwYXBvcnQuY29tL3VzZXIiOnsiYWNjb3VudElkIjo5NzMzNH0sImh0dHA6Ly9yYXBhcG9ydC5jb20vc2NvcGUiOlsicHJpY2VMaXN0V2Vla2x5Il0sImh0dHA6Ly9yYXBhcG9ydC5jb20vYXBpa2V5Ijp7Imh0dHBzOi8vcHJpY2VsaXN0LnJhcG5ldGFwaXMuY29tIjoiTmNYYWxRY01vbTl0ZDEwTnRZbTQ0M0dETU05VHBVbFc3OGRiTXNieiJ9LCJodHRwOi8vcmFwYXBvcnQuY29tL2F1ZGllbmNlIjpbImh0dHBzOi8vcHJpY2VsaXN0LnJhcG5ldGFwaXMuY29tIiwiaHR0cHM6Ly9hcGlnYXRld2F5LnJhcG5ldGFwaXMuY29tIl0sImh0dHA6Ly9yYXBhcG9ydC5jb20vcGVybWlzc2lvbnMiOnsicmFwbmV0YXBpcy1hcGlnYXRld2F5IjpbIm1lbWJlckRpcmVjdG9yeSIsInByaWNlTGlzdFdlZWtseSIsInByaWNlTGlzdE1vbnRobHkiLCJyYXBuZXRQcmljZUxpc3RXZWVrbHkiLCJiYXNpYyIsInJhcG5ldFByaWNlTGlzdE1vbnRobHkiLCJyYXBuZXRMaWdodCIsInNlYXJjaCIsImluc3RhbnRJbnZlbnRvcnlTZXR1cCIsIm1hbmFnZUxpc3RpbmdzRmlsZSIsImJ1eVJlcXVlc3RzQWRkIiwiaXRlbVNoYXJlZCIsInRyYWRlQ2VudGVyIiwibXlDb250YWN0cyIsIm1lbWJlclJhdGluZyIsImNoYXQiLCJsZWFkcyIsImFkbWluIiwiYnV5UmVxdWVzdHMiXX0sImlzcyI6Imh0dHBzOi8vcmFwYXBvcnQuYXV0aDAuY29tLyIsInN1YiI6IjNtaEEwTERYUDRaYWdEZ2JaRmlxVEVZQ2ZGaG5LeFFPQGNsaWVudHMiLCJhdWQiOiJodHRwczovL2FwaWdhdGV3YXkucmFwbmV0YXBpcy5jb20iLCJpYXQiOjE2OTU5MzE5OTEsImV4cCI6MTY5NjAxODM5MSwiYXpwIjoiM21oQTBMRFhQNFphZ0RnYlpGaXFURVlDZkZobkt4UU8iLCJzY29wZSI6ImFwaUdhdGV3YXkiLCJndHkiOiJjbGllbnQtY3JlZGVudGlhbHMifQ.t2mdF-C0uYaXYCfKLQwxQ1Xtg-80MpRsM292UgoQgsMnMyn2c_BR4-ALx0avEnAdmX8OknRLgJLqt7hNYkodQg6KeaNAlfrgTmp5lCYJGYhD1-TjYVQ_jo8s_mLoGGw6vwO6z1iE9FmTAH8OLPKo_0yzqXMSrl5zTSGtGigJTPZrZ3453xQ8kyFTWguyKKcXxsKlvCVCXi5PaPdt9LZL5hr-sdna-boOVW8ovocqGPj46W2yUQUJ0fiLNjY7-b1L695OHdowCcNZazJ3faDd4U6HdA_83OnVpeqZhQfXTP8kYFQhO_2Kgi8PbWsAOoS6gsbs1sshKUW31mKcf1U5MQ"
        shape_name = self.env['rapaport.api.shape'].search_read(
            [('active', '=', True)], ['name'])
        for shape in shape_name:
            shape_name = shape.get('name')
            response_datas += rapnet_api.get_price_sheet(shape_name)
            # request_params = {
            #     'shape': shape_name,
            #     'csvnormalized': True,

            # }
            # response = requests.get(
            #     get_price_endpoint,
            #     headers=headers,
            #     params=request_params,
            #     auth=BearerAuth(access_token)
            # )
            # if response.status_code == 200:
            #     price_data = json.loads(response.text)
            #     response_datas += price_data
            # else:
            #     _logger.info("Error in getting price from API")
            #     _logger.info(response.text)
        return response_datas

    def _genarate_price_sheet_sql(self, response_data):
        shape = response_data.get('shape')
        color = response_data.get('color')
        clarity = response_data.get('clarity')
        unique_id = self._return_unique_id(shape, color, clarity)
        name = self._return_name(shape, color, clarity)
        caratprice = response_data.get('caratprice')
        low_size = response_data.get('low_size')
        high_size = response_data.get('high_size')
        date = response_data.get('date')
        if date:
            date = parse_date(self.env, date).strftime("%Y-%m-%d")
        else:
            date = 'NULL'

        sql = f"""
            INSERT INTO rapaport_api_price (shape, color, clarity, caratprice, unique_id, name, date, low_size, high_size)
            VALUES ('{shape}', '{color}', '{clarity}', {float(caratprice)}, '{unique_id}', '{name}', '{date}', '{low_size}', '{high_size}')
        """
        return sql

    @api.model
    def create_price_records(self):
        response_datas = self.get_price_from_api()
        print(response_datas)
        for response_data in response_datas:
            try:
                sql = self._genarate_price_sheet_sql(response_data)
                self.env.cr.execute(sql)

            except Exception as e:
                _logger.error(e)
        if response_datas:
            self.env.cr.commit()


      
