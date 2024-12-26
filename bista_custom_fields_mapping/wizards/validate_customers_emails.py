# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, models,fields
import neverbounce_sdk
import re
import logging
from odoo.exceptions import ValidationError
from urllib.error import HTTPError
import requests

_logger = logging.getLogger(__name__)
regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'

class ValidateCustomersEmails(models.TransientModel):
    _name = 'validate.customers.emails'
    _description = 'Validate Customers Emails'

    # @api.multi
    def check_customers_emails(self):

        active_ids = self.env.context.get('active_ids')

        if active_ids:
            customers = self.env['res.partner'].search([('id','in',active_ids),('customer_rank','>',0),('email','!=',False),('is_blacklisted','!=',True),('email_validated','!=',True)])

            for customer in customers:
                self.email_validator(customer)
                _logger.log('Customer %s Email Validated', customer.name)

        else:
            all_customers = self.env['res.partner'].search([('customer_rank','>',0),('email','!=',False),('is_blacklisted','!=',True),('email_validated','!=',True)])

            for customer in all_customers:
                self.email_validator(customer)
                _logger.info('Customer %s Email Validated',customer.name)

        return True

    def has_business_with_us(self,partner):
        crm_check = self.env['crm.lead'].search_count([('active','in',('true','false')) , ('partner_id','=',partner.id) ])
        sales_check = self.env['sale.order'].search_count([('partner_id','=',partner.id)])
        pos_check = self.env['pos.order'].search_count([('partner_id','=',partner.id)])
        invoices_check = self.env['account.move'].search_count([('partner_id','=',partner.id)])
        history_check = self.env['client.history'].search_count([('partner_id','=',partner.id)])
        purchase_order_check = self.env['purchase.order'].search_count([('partner_id','=',partner.id)])

        if crm_check > 0 or sales_check > 0 or pos_check > 0 or invoices_check > 0 or history_check > 0 or purchase_order_check > 0:
            return True
        else:
            return False

    def email_validator(self,partner):
        api_key = self.env['ir.config_parameter'].sudo().get_param('neverbounce_api_key') or ''
        client = neverbounce_sdk.client(api_key=api_key, timeout=30)
        if ',' in partner.email:
            emails = partner.email.split(',')
            validated_emails = []
            i = 0
            while i < len(emails):
                if (re.search(regex, emails[i])):
                    resp = client.single_check(emails[i])
                    if resp.get('status') == 'success':
                        if resp.get('result') != 'invalid':
                            validated_emails.append(emails[i])
                    else:
                        _logger.critical('Please check your api billing plan')

                i += 1

            validated_emails_str = ','.join(map(str, validated_emails))

            if validated_emails_str != '' :
                partner.write({'email': validated_emails_str,'email_validated':True,'email_validated_date':fields.Datetime.now()})
                self._cr.commit()
            elif validated_emails_str == '':
                if self.has_business_with_us(partner):
                    partner.write({'email': ''})
                    self._cr.commit()

                elif partner.mobile or partner.street or partner.phone:
                     partner.write({'email': ''})
                     self._cr.commit()

                else:
                    partner.write({'delete_customer':True})
                    self._cr.commit()
        else:
            if (re.search(regex, partner.email)):
                resp = client.single_check(partner.email)
                if resp.get('status') == 'success':
                    if resp.get('result') == 'invalid':
                        if self.has_business_with_us(partner):
                            partner.write({'email': ''})
                            self._cr.commit()

                        elif partner.mobile or partner.street or partner.phone:
                             partner.write({'email': ''})
                             self._cr.commit()
                        else:
                            partner.write({'delete_customer':True})
                            self._cr.commit()
                    else:
                        partner.write({'email_validated': True, 'email_validated_date': fields.Datetime.now()})
                        self._cr.commit()
                else:
                        _logger.critical('Please check your api billing plan')
            else:
                if self.has_business_with_us(partner):
                    partner.write({'email': ''})
                    self._cr.commit()

                elif partner.mobile or partner.street or partner.phone:
                    partner.write({'email': ''})
                    self._cr.commit()
                else:
                    partner.write({'delete_customer':True})
                    self._cr.commit()

    # @api.multi
    def search_jobs(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param('neverbounce_api_key') or ''
        client = neverbounce_sdk.client(api_key=api_key, timeout=30)
        # Get job's results
        try:
            jobs = client.jobs_results(job_id=3926139)
        except:
            raise ValidationError("Internal Server Error Please Contact the API Provider")

        # Iterate through jobs
        for job in jobs:
            if job.get('data').get('email') != 'email':
                if job.get('verification').get('result') != 'valid' and ',' not in job.get('data').get('email') :

                    res_partner = self.env['res.partner'].search([('email', 'ilike', job.get('data').get('email'))])
                    for partner in res_partner:
                        # if ',' in partner.email:
                        #
                        #     print(partner.email)
                        #     emails = partner.email.split(',')
                        #     emails.remove(job.get('data').get('email'))
                        #
                        #     validated_emails_str = ','.join(map(str, emails))
                        #
                        #     if validated_emails_str != '':
                        #         partner.write({'email':validated_emails_str,'email_validated': True, 'email_validated_date': fields.Datetime.now()})
                        #     elif validated_emails_str == '':
                        #         if self.has_business_with_us(partner):
                        #             partner.write({'email': None})
                        #             self._cr.commit()
                        #
                        #         elif partner.mobile or partner.street or partner.phone:
                        #             partner.write({'email': None})
                        #             self._cr.commit()
                        #
                        #         else:
                        #             partner.write({'delete_customer': True})
                        #             self._cr.commit()
                        #
                        # else:
                        if self.has_business_with_us(partner):
                            partner.write({'email': '','invalid_email_address':True, 'email_failure_reason' :job.get('verification').get('result') })
                            self._cr.commit()
                            _logger.info('Email %s Is %s' ,job.get('data').get('email'),job.get('verification').get('result'))

                        elif partner.mobile or partner.street or partner.phone:
                            partner.write({'email': '', 'invalid_email_address':True,'email_failure_reason' :job.get('verification').get('result')})
                            self._cr.commit()
                            _logger.info('Email %s Is %s' ,job.get('data').get('email'),job.get('verification').get('result'))

                        else:
                            partner.write({'delete_customer': True, 'invalid_email_address':True,'email_failure_reason' :job.get('verification').get('result')})
                            self._cr.commit()
                            _logger.info('Email %s Is %s' ,job.get('data').get('email'),job.get('verification').get('result'))

    # @api.multi
    def validate_multiple_emails(self):
        active_ids = self.env.context.get('active_ids')
        customers = self.env['res.partner'].search([('id', 'in', active_ids)])

        for partner in customers:
            api_key = self.env['ir.config_parameter'].sudo().get_param('neverbounce_api_key') or ''
            client = neverbounce_sdk.client(api_key=api_key, timeout=60)
            if ',' in partner.email:
                emails = partner.email.split(',')
                validated_emails = []
                i = 0
                while i < len(emails):
                    resp = client.single_check(emails[i])
                    if resp.get('status') == 'success':
                        _logger.info(str(emails[i]) + '>>' +str(resp.get('result')))
                        if resp.get('result') == 'valid':
                            validated_emails.append(emails[i])
                    else:
                        _logger.critical('Please check your api billing plan')

                    i += 1

                validated_emails_str = ','.join(map(str, validated_emails))

                if validated_emails_str != '':
                    partner.write({'email': validated_emails_str, 'email_validated': True, 'email_validated_date': fields.Datetime.now()})
                    self._cr.commit()
                elif validated_emails_str == '':
                    if self.has_business_with_us(partner):
                        partner.write({'email': ''})
                        self._cr.commit()

                    elif partner.mobile or partner.street or partner.phone:
                        partner.write({'email': ''})
                        self._cr.commit()

                    else:
                        partner.write({'delete_customer': True})
                        self._cr.commit()



