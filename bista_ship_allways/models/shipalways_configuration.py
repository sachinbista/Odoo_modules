# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    ship_always_validation = fields.Boolean(string='Ship Always Configuration', config_parameter = 'bista_ship_allways.ship_always_validation')
    url = fields.Char(string='Url',config_parameter='bista_ship_allways.url')
    token = fields.Char(string='Token',config_parameter='bista_ship_allways.token')
