# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class SpringSystemConnection:

    def establish_connection(endpoint_url, config_id=False):
        data = ""
        headers = ""
        x = requests.request("GET", endpoint_url, headers=headers, data=data)
        response = json.loads(x.text)
        _logger.info('response %s', response)
        if response and x.reason == 'OK':
            return response
        elif response and x.reason != 'OK':
            error_message = x.reason
            if config_id:
                error_message = '%s - %s' % (config_id.name, error_message)
            raise UserError(_("%s") % error_message)
