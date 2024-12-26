# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    neverbounce_api_key = fields.Char(
        string='Neverbounce Api Key',
        config_parameter='bista_email_validator.neverbounce_api_key')
