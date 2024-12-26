##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import logging
from .. import shopify
import urllib.parse as urlparse
from odoo import fields, models, tools, _, registry
from odoo.exceptions import AccessError, ValidationError, UserError
from datetime import datetime, timedelta
import traceback

_logger = logging.getLogger(__name__)


def _get_name(cust_data):
    if cust_data.get('first_name') and cust_data.get('last_name'):
        cust_name = f"{cust_data['first_name']} {cust_data['last_name']}"
    elif cust_data.get('first_name') or cust_data.get('last_name'):
        cust_name = cust_data.get('first_name', '') or cust_data.get('last_name', '')
    else:
        cust_name = cust_data.get('email', '')
    return cust_name if cust_name else 'NAME NOT PROVIDED'


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

    def create_update_customer_from_webhook(self, res, shopify_config):
        shopify_log_line_obj = self.env['shopify.log.line'].sudo()
        log_line_vals = {
            'name': "Webhook Create/Update Customer",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_order',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            shopify_config.check_connection()
            name = "%s %s" % (res.get('first_name', ''),
                              res.get('last_name', ''))
            job_descr = _("WebHook Create/Update Customer:   %s") % (
                    name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': res.get('id') or '',
                'operation_type': 'import_customer',
                'parent_id': parent_log_line_id.id
            })
            user = self.env.ref('base.user_root')
            self.env["res.partner"].with_user(user).with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5).create_update_shopify_customers(
                    res, shopify_config, log_line_id)
            _logger.info("Started Process Of Creating Customer Via Webhook->" "Webhook->:")
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise Warning(_(e))


    def create_update_shopify_customers(self, cust_data, shopify_config_id, log_line_id):
        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))
        try:
            cust_name = _get_name(cust_data)
            cust_vals = {
                'customer_rank': 1,
                'name': cust_name,
                'email': cust_data.get('email'),
                'phone': cust_data.get('phone'),
                'comment': cust_data.get('note'),
                'sh_tax_exempt': cust_data.get('tax_exempt') or False,
                'accept_email_marketing': cust_data.get('accepts_marketing') or False,
                'category_id': [(6, 0, self._get_category_ids(cust_data))],
                'company_id': shopify_config_id.default_company_id.id,
            }

            # Get Address Data
            if cust_data.get('default_address'):
                address = cust_data.get('default_address')
                cust_vals.update({
                    'shopify_province': address.get('province'),
                    "shopify_province_code": address.get('province_code'),
                    'country_id': self._get_country(address).id if address.get('country_code') else False,
                    'state_id': self._get_state(address).id if address.get('province') and address.get(
                        "province_code") else False,
                    'shopify_company_name': address.get("company") if address.get('company') else False,
                    'street': address.get('address1', ''),
                    'street2': address.get('address2', ''),
                    'city': address.get('city', ''),
                    'zip': address.get('zip', ''),
                    'phone': cust_data.get('phone', '')
                })

            if 'message_follower_ids' in cust_vals:
                cust_vals.pop('message_follower_ids')

            partner = self.search(
                [('shopify_customer_id', '=', cust_data.get('id')), ('shopify_config_id', '=', shopify_config_id.id)])
            if not partner:
                cust_vals.update({
                    'shopify_customer_id': cust_data.get('id'),
                    'shopify_config_id': shopify_config_id.id
                })
                partner = self.create(cust_vals)
            else:
                partner.write(cust_vals)

            if len(cust_data.get('addresses')) > 1:
                for address in cust_data.get('addresses'):
                    contact_vals = {
                        'name': _get_name(address),
                        "shopify_province_code": address.get('province_code'),
                        'shopify_province': address.get('province'),
                        'country_id': self._get_country(address).id if address.get('country_code') else False,
                        'state_id': self._get_state(address).id if address.get('province') and address.get(
                            "province_code") else False,
                        'type': 'delivery',
                        'street': address.get('address1', ''),
                        'street2': address.get('address2', ''),
                        'city': address.get('city', ''),
                        'zip': address.get('zip', ''),
                        'phone': address.get('phone', ''),
                        'company_id': shopify_config_id.default_company_id.id
                    }
                    contact = self.search([('shopify_address_id', '=', address.get('id')),
                                           ('shopify_config_id', '=', shopify_config_id.id)])
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
            log_line_id.update({
                'state': 'success',
                'related_model_name': 'res.partner',
                'related_model_id': partner.id,
                'message':'Operation Successful'
            })
            cr.commit()
        except Exception as e:
            cr.rollback()
            log_line_id.update({
                'state': 'error',
                'message': 'Failed to import Customers : {}'.format(e)
            })
            self.env.cr.commit()
            raise Warning(_(e))

    def _get_category_ids(self, cust_data):
        tags_env = self.env['res.partner.category']
        tags = cust_data.get('tags', False)
        if tags != '':
            tags = cust_data.get('tags', False).split(',')
            return [
                tags_env.search([('name', '=', tag)])[0].id if tags_env.search([('name', '=', tag)]) else tags_env.create(
                    {'name': tag}).id for tag in tags]
        else:
            return []


    def _get_country(self, address):
        country_env = self.env['res.country']
        country_code = address.get('country_code', '')
        country_name = address.get('country_name', '')

        country = country_env.search([('code', '=', country_code)], limit=1)
        if not country:
            country = country_env.create({'name': country_name, 'code': country_code})

        return country

    def _get_state(self, address):
        state_env = self.env['res.country.state']
        country = self._get_country(address)
        province = address.get('province', '')
        province_code = address.get('province_code', '') or 'N/A'

        state = state_env.search([
            '|',
            ('name', '=', province),
            ('code', '=', province_code),
            ('country_id', '=', country.id if country else False),
        ], limit=1)

        if not state:
            state = state_env.create({
                'name': province,
                'code': province_code,
                'country_id': country.id if country else False
            })
        return state

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
                                       shopify_customer_by_ids=False):
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Customers",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_customer',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        try:
            # TODO: Handle multiple customer ids
            # customer_list = []
            # for customer in ''.join(shopify_customer_by_ids.split()).split(','):
            #     customer_list.append(shopify.Customer().find(customer))
            res_partner_obj = self.env['res.partner']
            shopify_log_line_obj = self.env['shopify.log.line']
            shopify_config.check_connection()
            customer_list = shopify.Customer().find(ids=str(shopify_customer_by_ids))
            # shopify_log_id = self._context.get('shopify_log_id')
            for shopify_customer in customer_list:
                shopify_customer_dict = shopify_customer.to_dict()
                name = shopify_customer_dict.get('first_name', '') if shopify_customer_dict.get('first_name',
                                                                                                '') else ''
                if name:
                    name += ' '
                name += shopify_customer_dict.get('last_name', '') if shopify_customer_dict.get('last_name', '') else ''
                if not name:
                    name = shopify_customer_dict.get('email', '')

                job_descr = _("Create/Update Customer:   %s") % (name and name.strip())

                log_line_id = shopify_log_line_obj.create({
                    'name': job_descr,
                    'shopify_config_id': shopify_config.id,
                    'id_shopify': f"Customer: {shopify_customer_dict.get('id') or ''}",
                    'operation_type': 'import_customer',
                    'parent_id': parent_log_line_id.id,
                })
                res_partner_obj.create_update_shopify_customers(shopify_customer_dict, shopify_config, log_line_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': traceback.format_exc(),
            })
            # self.env.cr.commit()
            # raise Warning(_(e))

    def shopify_import_customers(self, shopify_config):
        """This method is used to create queue and queue line for customers"""
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Customers",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_customer',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            res_partner_obj = self_cr.env['res.partner']
            shopify_config.check_connection()
            last_import_customer_date, parameter_id = (
                shopify_config.get_update_value_from_config(
                    operation='read', field='last_import_customer_date',
                    shopify_config_id=shopify_config, field_value=''))
            shopify_customer_list = self_cr.fetch_all_shopify_customers(last_import_customer_date)
            if shopify_customer_list:
                seconds = 10
                for customer in shopify_customer_list:
                    customer_dict = customer.to_dict()
                    name = customer_dict.get('first_name', '') if customer_dict.get('first_name', '') else ''
                    if name:
                        name += ' '
                    name += customer_dict.get('last_name', '') if customer_dict.get('last_name', '') else ''
                    if not name:
                        name = customer_dict.get('email', '')

                    job_descr = _("Create/Update Customer:   %s") % (name and name.strip())
                    log_line_vals.update({
                        'name': job_descr,
                        'id_shopify': f"Customer: {customer_dict.get('id') or ''}",
                        'parent_id': parent_log_line_id.id
                    })
                    log_line_id = shopify_log_line_obj.create(log_line_vals)
                    eta = datetime.now() + timedelta(seconds=seconds)
                    res_partner_obj.with_company(shopify_config.default_company_id).with_delay(description=job_descr, max_retries=5,
                                               eta=eta).create_update_shopify_customers(
                        customer_dict, shopify_config, log_line_id)
                    seconds += 2
            shopify_config.get_update_value_from_config(
                operation='write', field='last_import_customer_date', shopify_config_id=shopify_config,
                field_value=str(datetime.now().strftime('%Y/%m/%d %H:%M:%S')), parameter_id=parameter_id)

            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            cr.commit()
            return True
        except Exception as e:
            cr.rollback()
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise Warning(_(e))
