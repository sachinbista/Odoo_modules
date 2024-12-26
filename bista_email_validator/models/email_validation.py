# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from email_validator import validate_email, EmailNotValidError
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import neverbounce_sdk
import logging

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    invalid_email_address = fields.Boolean(string='Invalid Email')
    email_failure_reason = fields.Char(string='Reason')

    email_validated = fields.Boolean(string='Is Email Validated')
    email_validated_date = fields.Datetime(string='Email Validate Date')
    delete_customer = fields.Boolean(string='Needed To Be Deleted')

    @api.constrains('email')
    def validate_email(self):
        try:
            '''
            Check that the email address is valid. Turn on check_deliverability
            for first-time validations like on account creation pages (but not
            login pages)
            '''
            api_key = self.env['ir.config_parameter'].sudo().get_param('bista_email_validator.neverbounce_api_key')
            if api_key:
                client = neverbounce_sdk.client(api_key=api_key, timeout=30)
                for record in self:
                    if record.email:
                        emailinfo = validate_email(record.email, check_deliverability=False)
                        email = emailinfo.normalized
                        try:
                            resp = client.single_check(email)
                            _logger.info(F"Email Validation Response : {resp}")
                            if resp.get('status') == 'success':
                                if resp.get('result') not in ('valid', 'catchall'):
                                    self.update({
                                        'invalid_email_address': True,
                                        'email_failure_reason': str(resp.get('flags'))
                                        })
                                    raise ValidationError(_('"%s" is invalid email address') % email)
                                else:
                                    self.update({
                                        'invalid_email_address': False,
                                        'email_failure_reason': '',
                                        })
                            else:
                                raise ValidationError('Please check your api billing plan')
                        except Exception as ex:
                            raise ValidationError(ex)
        except EmailNotValidError as e:
            raise ValidationError((str(e)))
