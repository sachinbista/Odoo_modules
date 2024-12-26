# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    auto_print_config_validation = fields.Boolean(string='Auto Print Configuration', config_parameter = 'flybar_custom_inventory_report.auto_print_config_validation')