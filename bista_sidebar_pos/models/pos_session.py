# -*- coding: utf-8 -*-
# Part of Bistasolutions. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, tools
import logging

_logger = logging.getLogger(__name__)

class POSSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_users(self):
        result = super()._loader_params_res_users()
        result['search_params']['fields'].extend(['is_allow_sidebar'])
        return result

    def _loader_params_hr_employee(self):
        result = super()._loader_params_hr_employee()
        result['search_params']['fields'].extend(['is_allow_sidebar'])
        return result
