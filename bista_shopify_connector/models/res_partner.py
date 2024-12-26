##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

import pprint
from .. import shopify
import urllib.parse as urlparse
from odoo import fields, models, tools
from odoo.exceptions import AccessError, ValidationError
from datetime import datetime, timedelta


class Partner(models.Model):
    _inherit = "res.partner"

    shopify_province = fields.Char("Shopify Province", copy=False)
    shopify_province_code = fields.Char("Shopify Province Code", copy=False)
    shopify_company_name = fields.Char("Shopify Company", copy=False)
    sh_tax_exempt = fields.Boolean(string='Tax Exempt', copy=False)
    shopify_customer_id = fields.Char(string='Shopify Customer ID', copy=False)
    shopify_address_id = fields.Char(string='Shopify Address ID', copy=False)
    accept_email_marketing = fields.Boolean(string="Accept Email Marketing",
                                            copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)

    def create_update_shopify_customers(self, customer_dict, shopify_config_id):
        tags_env = self.env['res.partner.category']
        state_env = self.env['res.country.state']
        country_env = self.env['res.country']
        error_log_env = self.env['shopify.error.log']
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        try:
            cust_data = customer_dict
            cust_vals = {'customer_rank': 1}
            # Get Tags/ Partner Category
            category_ids = []
            if cust_data.get('first_name', '') and \
                    cust_data.get('last_name', False):
                cust_name = "%s %s" % (cust_data.get('first_name', ''),
                                       cust_data.get('last_name', ''))
            elif cust_data.get('first_name', '') or \
                    cust_data.get('last_name', ''):
                cust_name = cust_data.get('first_name', '') or \
                            cust_data.get('last_name', '')
            else:
                cust_name = cust_data.get('email', '')
            if cust_name in (False, None, ''):
                cust_name = 'NAME NOT PROVIDED'
            cust_vals.update({
                'name': cust_name,
                'email': cust_data.get('email'),
                'phone': cust_data.get('phone'),
                'comment': cust_data.get('note'),
                'sh_tax_exempt': cust_data.get('tax_exempt') or False,
                'accept_email_marketing':
                    cust_data.get('accepts_marketing') or False,
                'property_account_receivable_id': shopify_config_id.default_rec_account_id.id,
                'property_account_payable_id' : shopify_config_id.default_pay_account_id.id,
                'is_automatically_created': True
            })
            tags = cust_data.get('tags') and cust_data.get(
                'tags').split(',') or []
            for tag in tags:
                res = tags_env.search([('name', '=', tag)])
                if not res:
                    res = tags_env.create({'name': tag})
                category_ids.append(res[0].id)
            cust_vals.update({'category_id': [(6, 0, category_ids)]})
            # Get Address Data
            if cust_data.get('default_address'):
                address = cust_data.get('default_address')
                cust_vals.update({'shopify_province': address.get('province'),
                                  "shopify_province_code": address.get(
                                      'province_code')})
                country = False
                if address.get('country_code'):
                    country = country_env.search(
                        [('code', '=', address.get('country_code', ''))],
                        limit=1)
                    if not country:
                        country = country_env.create(
                            {'name': address.get('country_name', ''),
                             'code': address.get('country_code', '')})
                    cust_vals.update({'country_id': country.id})

                if address.get('province') and address.get(
                        "province_code"):
                    state = state_env.search(
                        ['|', ('name', '=', address.get('province')),
                         ('code', '=', address.get('province_code')),
                         ('country_id', '=', country and country.id or False
                          )],
                        limit=1)
                    if not state:
                        state = state_env.create({
                            'name': address.get('province', ''),
                            'code': address.get('province_code', '') or 'N/A',
                            'country_id': country and country.id or False
                        })
                    cust_vals.update({'state_id': state.id})

                if address.get('company'):
                    cust_vals['shopify_company_name'] = address.get(
                        "company")

                cust_vals.update({
                    'street': address.get('address1', ''),
                    'street2': address.get('address2', ''),
                    'city': address.get('city', ''),
                    'zip': address.get('zip', ''),
                    'phone': cust_data.get('phone', '')
                })
            if 'message_follower_ids' in cust_vals:
                cust_vals.pop('message_follower_ids')
            partner = self.search(
                [('shopify_customer_id', '=', cust_data.get('id'))])
            if not partner:
                cust_vals.update({
                    'shopify_customer_id': cust_data.get('id'),
                    'shopify_config_id': shopify_config_id.id
                })
                partner = self.create(cust_vals)
            else:
                partner.write(cust_vals)
            if len(cust_data.get('addresses')) > 1:
                for addresses in cust_data.get('addresses'):
                    address = addresses
                    cust_name = ''
                    if address.get('first_name', '') and \
                            address.get('last_name', False):
                        cust_name = address.get('first_name', '') + ' ' + \
                                    address.get('last_name', '')
                    elif address.get('first_name', '') or \
                            address.get('last_name', ''):
                        cust_name = address.get('first_name', '') or \
                                    address.get('last_name', '')
                    else:
                        cust_name = cust_vals.get('name', '')
                    if cust_name in (False, None, ''):
                        cust_name = 'NAME NOT PROVIDED'
                    contact_vals = {
                        'name': cust_name,
                        'phone': address.get('phone'),
                        "shopify_province_code": address.get(
                            'province_code'),
                        'shopify_province': address.get(
                            'province')
                    }
                    country = False
                    if address.get('country_code'):
                        country = country_env.search(
                            [('code', '=', address.get('country_code'))],
                            limit=1)
                        if not country:
                            country = country_env.create(
                                {'name': address.get('country_name'),
                                 'code': address.get('country_code')})
                        contact_vals.update({'country_id': country.id})

                    if address.get('province') and address.get(
                            'province_code'):
                        state = state_env.search(
                            ['|', ('name', '=', address.get("province")),
                             ('code', '=', address.get('province_code')),
                             ('country_id', '=', country and
                              country.id or False)], limit=1)
                        if not state:
                            state = state_env.create({
                                'name': address.get('province'),
                                'code': address.get(
                                    'province_code') or 'N/A',
                                'country_id': country and country.id or False
                            })
                        contact_vals.update({'state_id': state.id})
                    contact_vals.update({
                        'type': 'delivery',
                        'street': address.get('address1', ''),
                        'street2': address.get('address2', ''),
                        'city': address.get('city', ''),
                        'zip': address.get('zip', ''),
                        'phone': address.get('phone', '')
                    })
                    contact = self.search([(
                        'shopify_address_id', '=', address.get('id'))])
                    if not contact:
                        contact_vals.update({
                            'shopify_address_id': address.get('id'),
                            'shopify_config_id': shopify_config_id.id,
                            'customer_rank': 1,
                            'parent_id': partner.id
                        })
                        self.create(contact_vals)
                    else:
                        contact.write(contact_vals)
            # error_log_env.create_update_log(
            #     shop_error_log_id=shop_error_log_id,
            #     shopify_log_line_dict={'success': [
            #         {'error_message': "Import Customer %s Successfully" % cust_name,
            #          'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            if queue_line_id:
                queue_line_id.update({'state': 'processed', 'partner_id': partner.id})
        except Exception as e:
            error_message = 'Failed to import Customers : {}'.format(e)
            error_log_env.create_update_log(shop_error_log_id=shop_error_log_id,
                                            shopify_log_line_dict={'error': [
                                                {'error_message': error_message,
                                                 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.write({'state': 'failed'})
            pass

    def fetch_all_shopify_customers(self, last_import_customer_date):
        """return: shopify customer list
        TODO: fetch customer based on since_id"""
        try:
            shopify_customer_list = []
            page_info = False
            while 1:
                if last_import_customer_date:
                    # fixed issued fetch customer delay one minutes.
                    customer_date = last_import_customer_date - timedelta(minutes=1)
                    if page_info:
                        page_wise_customer_list = shopify.Customer().find(
                            limit=250, page_info=page_info)
                    else:
                        page_wise_customer_list = shopify.Customer().find(
                            updated_at_min=customer_date,
                            limit=250)
                else:
                    if page_info:
                        page_wise_customer_list = shopify.Customer().find(
                            limit=250, page_info=page_info)
                    else:
                        page_wise_customer_list = shopify.Customer().find(
                            limit=250)
                page_url = page_wise_customer_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and \
                            parsed.get('page_info', False)[0] or False
                shopify_customer_list = page_wise_customer_list + shopify_customer_list
                if not page_info:
                    break
            return shopify_customer_list
        except Exception as e:
            # TODO: Raise error log
            raise AccessError(e)

    def shopify_import_customer_by_ids(self, shopify_config,
                                      shopify_customer_by_ids=False, queue_line=None):
        # TODO: Handle multiple customer ids
        # customer_list = []
        # for customer in ''.join(shopify_customer_by_ids.split()).split(','):
        #     customer_list.append(shopify.Customer().find(customer))
        res_partner_obj = self.env['res.partner']
        shopify_config.check_connection()
        # customer_list = shopify.Customer().find(customer_id=shopify_customer_by_ids)
        customer_list = shopify.Customer().find(ids=str(shopify_customer_by_ids))
        shopify_log_id = self._context.get('shopify_log_id')
        for shopify_customer in customer_list:
            shopify_customer_dict = shopify_customer.to_dict()
            res_partner_obj.with_context(queue_line_id=queue_line,
                                         shopify_log_id=queue_line and queue_line.shop_queue_id.shopify_log_id \
                                        or shopify_log_id).create_update_shopify_customers(
                                            shopify_customer_dict, shopify_config)

    def shopify_import_customers(self, shopify_config):
        """This method is used to create queue and queue line for customers"""
        shopify_config.check_connection()
        last_import_customer_date = shopify_config.last_import_customer_date or False
        shopify_customer_list = self.fetch_all_shopify_customers(last_import_customer_date)
        if shopify_customer_list:
            for shopify_customers in tools.split_every(250, shopify_customer_list):
                shop_queue_id = shopify_config.action_create_queue('import_customer')
                for customer in shopify_customers:
                    customer_dict = customer.to_dict()
                    name = "%s %s" % (customer_dict.get('first_name', ''),
                                      customer_dict.get('last_name', ''))
                    line_vals = {
                        'shopify_id': customer_dict.get('id') or '',
                        'state': 'draft',
                        'name': name and name.strip(),
                        'record_data': pprint.pformat(customer_dict),
                        'shopify_config_id': shopify_config.id,
                    }
                    shop_queue_id.action_create_queue_lines(line_vals)
        shopify_config.last_import_customer_date = fields.Datetime.now()
        return True
