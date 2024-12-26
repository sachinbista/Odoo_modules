# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    cargo_spectre_validation = fields.Boolean(string='Cargo Spectre Configuration', config_parameter = 'custom_quality_check.cargo_spectre_validation')
    spectre_url = fields.Char(string='Url',config_parameter='custom_quality_check.url')
    spectre_token = fields.Char(string='Token',config_parameter='custom_quality_check.token')
    image_path_url = fields.Char(string='Image Path Url', config_parameter='custom_quality_check.image_path_url')
    image_url = fields.Char(string='Image Url', config_parameter='custom_quality_check.image_url')
