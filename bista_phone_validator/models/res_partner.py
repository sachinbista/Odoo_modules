# -*- encoding: utf-8 -*-

from odoo import models, api
from odoo.exceptions import ValidationError

import requests
import json
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def validate_number(self, number=False):
        if number:
            company_id = self.env.user.company_id
            if company_id.allow_phone_validation and company_id.phone_validation_key:
                api_key = company_id.phone_validation_key
                valid_number = False
                try:
                    response = requests.get(
                        F"https://phonevalidation.abstractapi.com/v1/?api_key={api_key}&phone={number}")
                    if response and response.content:
                        response_content = json.loads(response.content.decode('utf-8'))
                        _logger.info(F"Number Validation Response {response_content}")
                        # response_type = response_content['type'] or False
                        if response_content['valid']:
                            prefix = response_content['country']['prefix']
                            if prefix == '+1':
                                valid_number = prefix + ' ' + response_content['format']['local']
                except Exception as ex:
                    raise ValidationError(ex)
                return valid_number

    @api.onchange('phone')
    def onchange_phone(self):
        ctx = dict(self.env.context) or {}
        if self.phone and ctx.get('phone_change', False):
            company_id = self.env.user.company_id
            if company_id.allow_phone_validation and company_id.phone_validation_key:
                phone_number = self.validate_number(number=self.phone)
                if phone_number:
                    self.phone = phone_number
                else:
                    raise ValidationError(
                        F"Customer name: {self.name}\nPhone Number: {self.phone} is invalid !")

    @api.onchange('mobile')
    def onchange_mobile(self):
        ctx = dict(self.env.context) or {}
        if self.mobile and ctx.get('mobile_change', False):
            company_id = self.env.user.company_id
            if company_id.allow_phone_validation and company_id.phone_validation_key:
                mobile_number = self.validate_number(number=self.mobile)
                if mobile_number:
                    self.mobile = mobile_number
                else:
                    raise ValidationError(
                        F"Customer name: {self.name}\nMobile Number: {self.mobile} is invalid !")
