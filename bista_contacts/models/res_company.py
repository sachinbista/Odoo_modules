# -*- encoding: utf-8 -*-

from odoo import models, _, api, fields
from odoo.exceptions import ValidationError

import requests
import re


class ResCompany(models.Model):
    _inherit = 'res.company'

    allow_address_validation = fields.Boolean(string='Allow Address Validation')
    card_comp_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Card Completion Fields',
        domain=[('model_id.model', '=', 'res.partner')])
    phone_validation_key = fields.Char(
        string='Phone/Mobile Validation Key')
    allow_phone_validation = fields.Boolean(string='Allow Phone/Mobile Validation')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_address_validation = fields.Boolean(
        related='company_id.allow_address_validation',
        string='Allow Address Validation',
        readonly=False)
    card_comp_field_ids = fields.Many2many(
        'ir.model.fields',
        related='company_id.card_comp_field_ids',
        string='Card Completion Fields',
        domain=[('model_id.model', '=', 'res.partner')],
        readonly=False)
    phone_validation_key = fields.Char(
        related='company_id.phone_validation_key',
        string='Phone/Mobile Validation Key',
        readonly=False)
    allow_phone_validation = fields.Boolean(
        related='company_id.allow_phone_validation',
        string='Allow Phone/Mobile Validation',
        readonly=False)
