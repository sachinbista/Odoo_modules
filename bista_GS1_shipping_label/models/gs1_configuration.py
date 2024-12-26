# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    gs1_shipping_label_validation = fields.Boolean(string='GS1 Shipping Label Configuration', config_parameter = 'bista_GS1_shipping_label.gs1_shipping_label_validation')
    gs1_extension_digit = fields.Integer(string='Extension Digit',config_parameter='bista_GS1_shipping_label.gs1_extension_digit')
    gs1_company_prefix = fields.Char(string='Company Prefix',config_parameter='bista_GS1_shipping_label.gs1_company_prefix')
    gs1_application_identifier = fields.Char(string='Application Identifier', config_parameter='bista_GS1_shipping_label.gs1_application_identifier')
