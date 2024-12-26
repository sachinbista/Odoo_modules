# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################


import json
import logging

import requests
from odoo.exceptions import UserError

from odoo import _

_logger = logging.getLogger(__name__)

headers = {'X-Beta-Contact': "mendel@rooteam.net"}

class GoFlowConnection:

    def establish_connection(x_beta_contact, authorization, goflow_login_url, config_id=False):
        if authorization:
            authorization = 'Bearer ' + authorization
        authorization = authorization
        data = ""
        headers = {'X-Beta-Contact': x_beta_contact, 'Authorization': authorization}
        try:
            goflow_response = requests.request("GET", goflow_login_url, headers=headers, data=data)
            response = json.loads(goflow_response.text)
        except Exception as e:
            return e
        _logger.info('response %s', response)
        if response and goflow_response.reason == 'OK':
            response_data = response.get('data')
            return response_data
        elif response and goflow_response.reason != 'OK':
            error_message = goflow_response.reason
            if config_id:
                error_message = '%s - %s' % (config_id.name, error_message)
            raise UserError(_("%s") % (error_message))
