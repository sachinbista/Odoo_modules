# -*- coding: utf-8 -*-

import json
import logging
from odoo.addons.bista_shipstation.models.shipstation_request import ShipStationRequest
from odoo import http
from odoo.http import request
import requests

logger = logging.getLogger("Shipstation")


class Binary(http.Controller):

    def _get_carrier(self, company_id):
        try:
            company_id = int(company_id) or request.env.company.id
        except ValueError:
            company_id = request.env.company.id

        return request.env['delivery.carrier'].sudo().search(
            [('delivery_type', '=', 'shipstation'),
             ('company_id.id', '=', company_id)], limit=1)


    @http.route('/shipments/<company_id>', type='json', auth="public", methods=['POST'], csrf=False)
    def post_shipments(self, company_id=0, **kwargs):
        print("AAAAAAAAAAAAAAAAAAAAAAA------------------------")
        res_date = request.httprequest.data
        data = json.loads(res_date)
        resource_url = data.get('resource_url', False)
        ship_station = self._get_carrier(company_id)
        if not ship_station:
            logger.warning("Shipstation delivery method was not found")
            return

        ship_station.process_order(resource_url)
        return json.dumps({"message": "Api called Successfully", "status_code": 200})
