# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request, content_disposition
from odoo.addons.bista_wms_api.common import invalid_response, valid_response
from odoo.addons.bista_wms_api.controllers.controllers import validate_token

_logger = logging.getLogger(__name__)


class BistaWmsNotification(http.Controller):

    @validate_token
    @http.route("/api/post_user_token", type="json", auth="none", methods=["POST"], csrf=False)
    def post_user_token(self, **payload):
        _logger.info("/api/post_user_token POST payload: %s", payload)
        try:
            access_token = request.httprequest.headers.get("access-token")
            user_id = request.env['api.access_token'].sudo().search([('token', '=', access_token)], limit=1).user_id
            if user_id and request.httprequest.method == 'POST':
                # convert the bytes format to `list of dict` format
                req_data = json.loads(request.httprequest.data.decode())
                if 'push_token' in req_data['data'].keys():
                    push_token = req_data['data']['push_token']
                    if push_token != user_id.push_token:
                        user_id.push_token = push_token
                    return valid_response({'message': "User Push Token Updated."})
                return invalid_response("no_user_token", "No Push Token found.", 200)
        except Exception as e:
            _logger.exception("Error while updating user notification token for payload: %s", payload)
            error_msg = 'Error while updating user push notification token.'
            return invalid_response('bad_request', error_msg, 200)
