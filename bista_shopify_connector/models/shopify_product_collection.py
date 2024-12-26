##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from datetime import datetime, timedelta
from odoo import models, fields, api, _, registry
from .. import shopify
from odoo.exceptions import AccessError, ValidationError, UserError
import urllib
import base64
from datetime import time
import logging
import urllib.parse as urlparse


_logger = logging.getLogger(__name__)


class ShopifyProductCollection(models.Model):
    _name = 'shopify.product.collection'
    _description = 'Shopify Product Collection'

    name = fields.Char(string='Name')
    body_html = fields.Html("Description")
    handle = fields.Char("Handle")
    image = fields.Binary(string='Image')
    color = fields.Integer(string='Color', help='Enter the Color')
    type = fields.Selection([('manual', 'Manual'), ('automated', 'Automated')],
                            default='manual', string='Collection Type')
    sort_order = fields.Selection([
        ('alpha-asc', 'Alphabetically, in ascending order (A - Z)'),
        ('alpha-desc', 'Alphabetically, in descending order (Z - A)'),
        ('best-selling', 'By best-selling products'),
        ('created', 'By date created, in ascending order (oldest - newest)'),
        (
            'created-desc', 'By date created, in descending order (newest - oldest)'),
        ('manual', 'Order created by the shop owner'),
        ('price-asc', 'By price, in ascending order (lowest - highest)'),
        ('price-desc', 'By price, in descending order (highest - lowest)')],
        string="Sort Order", default="manual")
    published_scope = fields.Selection([
        ('web', 'Publish to the Online Store channel.'),
        ('global',
         'Publish to Online Store channel and the Point of Sale channel.')],
        string="Published Scope", default="web")

    shopify_id = fields.Char(string='Shopify ID', copy=False)
    shopify_config_id = fields.Many2one('shopify.config',
                                        string='Shopify Config', copy=False,
                                        required=True)
    active = fields.Boolean("Active", default=True)
    is_disjunctive = fields.Boolean(string="Disjunctive", copy=False,
                                    help="Whether the product must match all the rules to be included in the smart collection.\n"
                                         "True: Products only need to match one or more of the rules to be included in the smart collection.\n"
                                         "False: Products must match all of the rules to be included in the smart collection.")
    shopify_published = fields.Boolean("Published", copy=False)
    shopify_update_date = fields.Datetime("Update Date")
    shopify_publish_date = fields.Datetime("Publish Date")
    collection_condition_ids = fields.One2many("shopify.collection.condition",
                                               "shopify_collection_id",
                                               string="Conditions")
    shopify_product_tmpl_count = fields.Integer(string="Templates",
                                                compute="compute_shopify_product_tmpl_count")

    def update_collection_from_webhook(self, res, shopify_config):
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "WebHook Update Collections",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'update_collection',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            shopify_config.check_connection()
            name = res.get('title', '')
            job_descr = _("WebHook Update Collections:   %s") % (
                    name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': res.get('id') or '',
                'operation_type': 'update_collection',
                'parent_id': parent_log_line_id.id
            })
            type = ''
            try:
                collection_id = shopify.CustomCollection().find(str(res.get('id')))
                if collection_id:
                    type = 'manual'
            except Exception as e:
                if hasattr(e, "response"):
                    if e and e.response.code == 404:
                        collection_id = shopify.SmartCollection().find(str(
                            res.get('id')))
                        if collection_id:
                            type = 'automated'
                raise e
            if type:
                user = self.env.ref('base.user_root')
                self.env["shopify.product.collection"].with_user(user).with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5).create_update_collection(
                    res, type, shopify_config, log_line_id, parent_log_line_id)
                _logger.info("Started Process Of Updating Collection Via "
                             "Webhook->")
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

    def compute_shopify_product_tmpl_count(self):
        self.shopify_product_tmpl_count = self.env['shopify.product.template'].search_count([(
            'shopify_prod_collection_ids', 'in', self.id)])

    def action_open_shopify_product_tmpl(self):
        shopify_product_tmpl_ids = self.env[
            'shopify.product.template'].search([(
            'shopify_prod_collection_ids', 'in', self.id)])
        return {
            'name': _('Shopify Product Template'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'shopify.product.template',
            'context': self.env.context,
            'domain': [('id', 'in', shopify_product_tmpl_ids and
                        shopify_product_tmpl_ids.ids or [])]
        }

    def action_sync_collection_product_rel(self):
        shopify_config = self.shopify_config_id
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Link Shopify Product",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_collection',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        job_descr = _("Create/Update Collection with Product: %s") % (self.name)
        log_line_id2 = self.env['shopify.log.line'].create({
            'name': job_descr,
            'shopify_config_id': self.shopify_config_id.id,
            'id_shopify': f"Collection: {self.shopify_id or ''}",
            'operation_type': 'import_collection',
            'parent_id': parent_log_line_id.id,
        })
        eta = datetime.now() + timedelta(seconds=5)
        self.with_company(shopify_config.default_company_id).with_delay(
            description=job_descr,
            max_retries=5, eta=eta).update_product_collection_rel(
            log_line_id=log_line_id2)
        parent_log_line_id.update({
            'state': 'success',
            'message': 'Operation Successful'
        })

    def update_product_collection_rel(self, data={}, log_line_id=False):
        try:
            shopify_id = data.get('id', '')
            if not shopify_id and not data:
                shopify_id = self.shopify_id
            self.shopify_config_id.check_connection()
            shopify_prod_templ_obj = self.env['shopify.product.template']
            # if self.type == 'automated':
            #     collection = shopify.SmartCollection().find(
            #         shopify_id)
            # else:
            #     collection = shopify.CustomCollection().find(
            #         shopify_id)
            # product_datas = collection.products()
            shopify_customer_list = []
            since_id = 0
            while 1:
                product_datas = shopify.Product.find(
                    collection_id=shopify_id, limit=250, since_id=since_id)
                shopify_customer_list += product_datas
                if product_datas and len(product_datas) >= 250:
                    since_id = max([product.to_dict().get('id') for
                                    product in product_datas])
                else:
                    break

            linked_prod_shopify = []
            for product in shopify_customer_list:
                shopify_tmpl_id = product.to_dict().get('id')
                linked_prod_shopify.append(shopify_tmpl_id)
                shopify_prod_tmpl_id = shopify_prod_templ_obj.search([(
                    'shopify_prod_tmpl_id', '=', shopify_tmpl_id)])
                (shopify_prod_tmpl_id and
                 shopify_prod_tmpl_id.product_tmpl_id.write({
                     'prod_collection_ids': [(4, self.id)]}))

            if linked_prod_shopify:
                shopify_product_tmpl_ids = self.env['shopify.product.template'].search(
                    [('shopify_prod_collection_ids', 'in', self.id),
                     ('shopify_prod_tmpl_id', 'not in', linked_prod_shopify)])
            if not linked_prod_shopify:
                shopify_product_tmpl_ids = self.env[
                    'shopify.product.template'].search(
                    [('shopify_prod_collection_ids', 'in', self.id)])
            if shopify_product_tmpl_ids:
                for shop_tmpl_id in shopify_product_tmpl_ids:
                    shop_tmpl_id.product_tmpl_id.write({
                        'prod_collection_ids': [(3, self.id)]})
            log_line_id.update({
                'state': 'success',
                'related_model_name': 'shopify.product.collection',
                'related_model_id': self.id,
            })
        except Exception as e:
            log_line_id.update({
                'state': 'error',
                'message': 'Failed to import Collection : {}'.format(e)
            })
            raise Warning(_(e))

    def create_update_collection(self, data, type, shopify_config, log_line_id, parent_log_line_id_2):
        try:
            shopify_config.check_connection()
            shopify_id = data.get('id', '')
            handle = data.get('handle', '')
            title = data.get('title', '')
            body_html = data.get('body_html', '')
            sort_order = data.get('sort_order', '')
            published_scope = data.get('published_scope', '')
            updated_at = data.get('updated_at')
            published_at = data.get('published_at')
            shop_updated_at = shopify_config.convert_shopify_datetime_to_utc(
                updated_at)
            shop_published_at = shopify_config.convert_shopify_datetime_to_utc(
                published_at)
            collection_vals = {
                'name': title,
                'handle': handle,
                'body_html': body_html,
                'sort_order': sort_order,
                'published_scope': published_scope,
                'type': type,
                'shopify_update_date': shop_updated_at,
                'shopify_publish_date': shop_published_at,
                'shopify_published': True,
                'shopify_config_id': shopify_config.id,
            }
            if type == 'automated':
                disjunctive = data.get('disjunctive')
                rules_list = data.get('rules')
                if rules_list and isinstance(rules_list, list):
                    condition_vals = []
                    for conditions in rules_list:
                        # condition_dict = conditions.attributes
                        if isinstance(conditions, dict):
                            condition_vals.append((0, 0, {
                                'column': conditions.get('column'),
                                'relation': conditions.get('relation'),
                                'condition': conditions.get('condition')}))
                    collection_vals.update(
                        {'collection_condition_ids': condition_vals,
                         'is_disjunctive': disjunctive})

            image_data = False
            if type == 'manual' and 'image' in data:
                collection = shopify.CustomCollection().find(shopify_id)
                collection = collection.attributes
                if collection.get('image'):
                    image_data = collection.get('image')
            if type == 'automated' and 'image' in data:
                collection = shopify.SmartCollection().find(
                    shopify_id)
                collection = collection.attributes
                if collection.get('image'):
                    image_data = collection.get('image')
            # image_data = data.get('image', {})
            if image_data:
                image = image_data.attributes.get('src')
                try:
                    (filename, header) = urllib.request.urlretrieve(image)
                    with open(filename, 'rb') as f:
                        img = base64.b64encode(f.read())
                        collection_vals.update({'image': img})
                except Exception:
                    img = False
                    pass
            else:
                collection_vals.update({'image': False})
            collection_id = self.search([('shopify_id', '=', shopify_id)])
            if collection_id:
                # for unlink existing condition resolved duplicate issued
                existing_conditions = collection_id.collection_condition_ids
                if existing_conditions and collection_id.id == 17:
                    existing_conditions.unlink()
                collection_id.write(collection_vals)
            else:
                collection_vals.update({'shopify_id': shopify_id})
                collection_id = self.create(collection_vals)
            log_line_id.update({
                'state': 'success',
                'related_model_name': 'shopify.product.collection',
                'related_model_id': collection_id.id,
                'message': 'Operation Successful'
            })
            if collection_id:
                job_descr = _("Create/Update Collection with Product: %s") % (
                    data.get('title', ''))
                log_line_id2 = self.env['shopify.log.line'].create({
                    'name': job_descr,
                    'shopify_config_id': shopify_config.id,
                    'id_shopify': f"Collection: {data.get('id', '') or ''}",
                    'operation_type': 'import_collection',
                    'parent_id': parent_log_line_id_2.id
                })
                eta = datetime.now() + timedelta(seconds=30)
                collection_id.with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr,
                    max_retries=5, eta=eta).update_product_collection_rel(
                    data, log_line_id=log_line_id2)
            parent_log_line_id_2.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
        except Exception as e:
            parent_log_line_id_2.update({
                'state': 'error',
                'message': e,
            })
            log_line_id.update({
                'state': 'error',
                'message': 'Failed to import Collection : {}'.format(e)
            })
            self.env.cr.commit()
            raise Warning(_(e))

    def shopify_import_product_collection(self, shopify_config,
                                          list_of_collections=[], since_id=0):

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Collections",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_collection',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            seconds = 15
            shopify_config.check_connection()
            last_collection_import_date, parameter_id = (
                shopify_config.get_update_value_from_config(
                    operation='read', field='last_collection_import_date',
                    shopify_config_id=shopify_config, field_value=''))
            field_value = str(datetime.now().strftime('%Y/%m/%d %H:%M:%S'))

            page_info = False
            shopify_collection_list = []
            while 1:
                if last_collection_import_date:
                    last_collection_date = last_collection_import_date - timedelta(minutes=1)
                    if page_info:
                        smart_collections_list = shopify.SmartCollection().find(
                            limit=250, page_info=page_info,
                            updated_at_min=last_collection_date.strftime('%Y-%m-%dT%H:%M:%S%z') + '-04:00')
                    else:
                        smart_collections_list = shopify.SmartCollection().find(
                            limit=250, updated_at_min=last_collection_date.strftime('%Y-%m-%dT%H:%M:%S%z') + '-04:00')
                else:
                    if page_info:
                        smart_collections_list = shopify.SmartCollection().find(
                            limit=250, page_info=page_info)
                    else:
                        smart_collections_list = shopify.SmartCollection().find(
                            limit=250)
                page_url = smart_collections_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and \
                            parsed.get('page_info', False)[0] or False
                shopify_collection_list += smart_collections_list
                if not page_info:
                    break

            log_line_vals_2 = {
                'name': "Import Collection with Product",
                'shopify_config_id': shopify_config.id,
                'operation_type': 'import_collection',
            }
            parent_log_line_id_2 = shopify_log_line_obj.create(log_line_vals_2)
            for smart_collect in shopify_collection_list:
                # list_of_collections.append(smart_collect.id)
                smart_collect_data = smart_collect.attributes
                if smart_collect_data.get('image'):
                    smart_collect_data.update({'image': False})
                job_descr = _("Create/Update Collection: %s") % (smart_collect_data.get('title', ''))
                log_line_vals.update({
                    'name': job_descr,
                    'id_shopify': f"Collection: {smart_collect_data.get('id', '') or ''}",
                    'parent_id': parent_log_line_id.id
                })
                log_line_id = shopify_log_line_obj.create(log_line_vals)

                rules = smart_collect_data.get('rules', [])
                smart_collect_data['rules'] = [rule.to_dict() for rule in rules]
                eta = datetime.now() + timedelta(seconds=seconds)
                self_cr.with_company(shopify_config.default_company_id).with_delay(description=job_descr, max_retries=5, eta=eta
                                   ).create_update_collection(
                    smart_collect_data,
                    'automated',
                    shopify_config,
                    log_line_id, parent_log_line_id_2)
                seconds += 2

            page_info = False
            list_of_collections = []
            while 1:
                if last_collection_import_date:
                    # last_collection_date = last_collection_import_date - timedelta(minutes=1)
                    if page_info:
                        collections_list = shopify.CustomCollection().find(
                            limit=250, page_info=page_info,
                            updated_at_min=last_collection_import_date.strftime('%Y-%m-%dT%H:%M:%S%z') + '-04:00')
                    else:
                        collections_list = shopify.CustomCollection().find(
                            limit=250,
                            updated_at_min=last_collection_import_date.strftime('%Y-%m-%dT%H:%M:%S%z') + '-04:00')
                else:
                    if page_info:
                        collections_list = shopify.CustomCollection().find(
                            limit=250, page_info=page_info)
                    else:
                        collections_list = shopify.CustomCollection().find(
                            limit=250)
                page_url = collections_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and \
                            parsed.get('page_info', False)[0] or False
                list_of_collections += collections_list
                if not page_info:
                    break

            for collection in list_of_collections:
                # list_of_collections.append(collection.id)
                data = collection.attributes
                if data.get('image'):
                    data.update({'image': False})
                job_descr = _("Create/Update Collection: %s") % (data.get('title', ''))
                log_line_vals.update({
                    'name': job_descr,
                    'id_shopify': f"Collection: {data.get('id', '') or ''}",
                    'parent_id': parent_log_line_id.id
                })
                log_line_id = shopify_log_line_obj.create(log_line_vals)

                rules = data.get('rules', [])
                data['rules'] = [rule.to_dict() for rule in rules]
                eta = datetime.now() + timedelta(seconds=seconds)
                self_cr.with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5, eta=eta
                ).create_update_collection(data, 'manual', shopify_config,
                                           log_line_id, parent_log_line_id_2)
                seconds += 2

            shopify_config.get_update_value_from_config(
                operation='write', field='last_collection_import_date', shopify_config_id=shopify_config,
                field_value=field_value, parameter_id=parameter_id)

            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            cr.commit()
        except Exception as e:
            cr.rollback()

            if hasattr(e, "response"):
                if e and e.response.code == 429 and e.response.msg == "Too Many Requests":
                    time.sleep(5)
                    self.shopify_import_product_collection(shopify_config)

            error_msg = "Facing a problems while importing Collections!: %s" % e
            parent_log_line_id.update({
                'state': 'error',
                'message': error_msg,
            })
            self.env.cr.commit()
            raise Warning(_(e))

    def deactive_collection(self, collection_lists):
        col_ids = self.env['shopify.product.collection'].search([(
            'shopify_id', 'not in', collection_lists),
            ('shopify_config_id', '=', self.id)])
        if col_ids:
            col_ids.write({'active': False})
        return True

    def prepare_collection_vals(self):
        collection_vals = {'title': self.name}
        if self.body_html:
            collection_vals.update({'body_html': self.body_html})
        if self.sort_order:
            collection_vals.update({'sort_order': self.sort_order})
        if self.published_scope:
            collection_vals.update({'published_scope': self.published_scope})
        if self.image:
            collection_vals.update(
                {'image': {'attachment': self.image.decode("utf-8")}})
        if self.type == 'automated':
            collection_vals.update({'disjunctive': self.is_disjunctive})
            condition_list = []
            for condition_id in self.collection_condition_ids:
                condition_list.append({'column': condition_id.column,
                                       'relation': condition_id.relation,
                                       'condition': condition_id.condition})
            collection_vals.update({'rules': condition_list})
        return collection_vals

    @api.model
    def create(self, vals):
        '''Method override to update product collection on creation'''
        res = super(ShopifyProductCollection, self).create(vals)
        if not vals.get('shopify_id'):
            try:
                shopify_log_line_env = self.env['shopify.log.line']
                job_descr = _("Export Collection on Shopify: %s") % res.name
                log_line_id = shopify_log_line_env.create({
                    'name': job_descr,
                    'shopify_config_id': res.shopify_config_id.id,
                    'operation_type': 'export_collection',
                })
                res.shopify_config_id.check_connection()
                self.with_company(res.shopify_config_id.default_company_id).with_delay(
                    description=job_descr, max_retries=5
                ).export_collection_to_shopify(res, res.shopify_config_id,
                                               log_line_id)
            except Exception as e:
                error_msg = "Error on Export Manually/Automated Collection: %s" % e
                _logger.error(_(error_msg))
        return res

    def shopify_export_product_collection(self, shopify_config):

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Export Collections",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'export_collection',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        try:
            shopify_log_line_env = self.env['shopify.log.line']
            shopify_config.check_connection()
            for collection in self.search(['|',
                                           ('shopify_published', '=', False),
                                           ('shopify_id', '=', False),
                                           ('shopify_config_id', '=',
                                            shopify_config.id)]):
                job_descr = _("Create/Update Collection on Shopify: %s") % collection.name
                log_line_id = shopify_log_line_env.create({
                    'name': job_descr,
                    'shopify_config_id': shopify_config.id,
                    'operation_type': 'export_collection',
                    'parent_id': parent_log_line_id.id
                })
                self.with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5
                ).export_collection_to_shopify(collection, shopify_config,
                                               log_line_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
        except Exception as e:
            error_msg = "Error on Export Manually/Automated Collection: %s" % e
            parent_log_line_id.update({
                'state': 'error',
                'message': error_msg,
            })
            self.env.cr.commit()
            raise Warning(_(e))

    def export_collection_to_shopify(self, collection, shopify_config, log_line_id):
        try:
            if collection.type == 'manual':
                new_collection = shopify.CustomCollection()
                collection_vals = collection.prepare_collection_vals()
            else:
                new_collection = shopify.SmartCollection()
                collection_vals = collection.prepare_collection_vals()
            result = new_collection.create(collection_vals)
        except Exception as e:
            log_line_id.update({
                'state': 'error',
                'message': 'Failed to export Collection : {}'.format(e)
            })
            self.env.cr.commit()
            raise Warning(_(e))
        else:
            if not result.id:
                error_msg = "Getting response '%s' on Export Collection: Please review Conditions and Details." % result
                log_line_id.update({
                    'state': 'error',
                    'message': 'Failed to export Collection : {}'.format(error_msg)
                })
            else:
                collection.update({'shopify_id': result.id,
                                   'shopify_published': True,
                                   'shopify_config_id': shopify_config.id})
                log_line_id.update({
                    'state': 'success',
                    'id_shopify': f"Collection: {result.id}",

                })

    def prepare_update_collection_vals(self, new_collection):
        new_collection.title = self.name
        if self.body_html:
            new_collection.body_html = self.body_html
        if self.sort_order:
            new_collection.sort_order = self.sort_order
        if self.published_scope:
            new_collection.published_scope = self.published_scope
        if self.shopify_published:
            new_collection.published = self.shopify_published
        if self.image:
            new_collection.image = {'attachment': self.image.decode('UTF-8')}
        if self.type == 'automated':
            new_collection.disjunctive = self.is_disjunctive
            condition_list = []
            for condition_id in self.collection_condition_ids:
                condition_list.append({'column': condition_id.column,
                                       'relation': condition_id.relation,
                                       'condition': condition_id.condition})
            new_collection.rules = condition_list
        if self.type == 'manual':
            product_list = [prod.to_dict().get('id') for prod in
                            new_collection.products()]
            shopify_product_ids = self.env['shopify.product.template'].search([
                ('shopify_prod_tmpl_id', '!=', False),
                ('shopify_prod_tmpl_id', 'not in', product_list),
                ('shopify_prod_collection_ids', 'in', self.id)
            ])
            if shopify_product_ids:
                for shop_prod in shopify_product_ids:
                    product_template_dict = shopify.Product().find(
                        shop_prod.shopify_prod_tmpl_id)
                    new_collection.add_product(product_template_dict)

        return new_collection

    def btn_update_collection_in_shopify(self):
        shopify_config = self.shopify_config_id
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Update Collection In Shopify",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'update_collection',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        job_descr = _("Export Collection with Product: %s") % (self.name)
        log_line_id2 = self.env['shopify.log.line'].create({
            'name': job_descr,
            'shopify_config_id': self.shopify_config_id.id,
            'id_shopify': f"Collection: {self.shopify_id or ''}",
            'operation_type': 'update_collection',
            'parent_id': parent_log_line_id.id
        })
        eta = datetime.now() + timedelta(seconds=5)
        self.with_company(shopify_config.default_company_id).with_delay(
            description=job_descr,
            max_retries=5, eta=eta).update_collection_in_shopify(
            log_line_id=log_line_id2, )
        parent_log_line_id.update({
            'state': 'success',
            'message': 'Operation Successful'
        })

    def update_collection_in_shopify(self, log_line_id=False):
        self.shopify_config_id.check_connection() if self.shopify_config_id else False
        try:
            if self.shopify_published and self.shopify_id:
                if self.type == 'manual':
                    update_collection = shopify.CustomCollection().find(
                        self.shopify_id)
                    update_collection = self.prepare_update_collection_vals(
                        update_collection)
                else:
                    if not self.collection_condition_ids:
                        raise UserError("Please Add conditions for this automated "
                                        "collection")
                    update_collection = shopify.SmartCollection().find(
                        self.shopify_id)
                    update_collection = self.prepare_update_collection_vals(
                        update_collection)
                update_collection.save()
            if log_line_id:
                log_line_id.write({'state': 'success'})
        except Exception as e:
            log_line_id.write({'state': 'error', 'message': e})
            self.env.cr.commit()
            raise ValidationError(
                _("Error on Update Manually/Automated Collection: {}".format(e)))

    def shopify_update_product_colleciton_queue(self, log_line_id=False):
        self.shopify_config_id.check_connection()
        try:
            if self.type == 'manual':
                update_collection = shopify.CustomCollection().find(
                    self.shopify_id)
                update_collection = self.prepare_update_collection_vals(
                    update_collection)

            else:
                if not self.collection_condition_ids:
                    raise UserError(_(
                        "Please Add conditions in %s" % self.name))
                update_collection = shopify.SmartCollection().find(
                    self.shopify_id)
                update_collection = self.prepare_update_collection_vals(
                    update_collection)
            update_collection.save()
            collection = self.env['shopify.product.collection'].search([('shopify_id', '=', self.shopify_id)],
                                                                       limit=1)
            if log_line_id:
                log_line_id.write({'state': 'success',
                                   'related_model_name': 'shopify.product.collection',
                                   'related_model_id': collection.id,
                                   'message':'Operation Successful'
                                   })
        except Exception as e:
            log_line_id.write({'state': 'error',
                               'message': e,

                               })
            self.env.cr.commit()
            raise ValidationError(
                _("Error on Update Manually/Automated Collection: {}".format(e)))

    def shopify_update_product_collection(self, shopify_config):
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Update Collections",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'update_collection',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            for collection in self.search([('shopify_published', '=', True),
                                           ('shopify_id', '!=', False)]):
                job_descr = _("Export Collection with Product: %s") % (
                    collection.name)
                log_line_id = self.env['shopify.log.line'].create({
                    'name': job_descr,
                    'shopify_config_id': collection.shopify_config_id.id,
                    'id_shopify': f"Collection: {collection.shopify_id or ''}",
                    'operation_type': 'update_collection',
                    'parent_id': parent_log_line_id.id
                })
                eta = datetime.now() + timedelta(seconds=5)
                collection.with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr,
                    max_retries=5, eta=eta).shopify_update_product_colleciton_queue(
                    log_line_id=log_line_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful',
            })
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise Warning(_(e))


class ShopifyCollectionCondition(models.Model):
    _name = 'shopify.collection.condition'
    _description = 'Shopify Collection Condition'

    column = fields.Selection([
        ('title', 'Title',),
        ('type', 'Type',),
        ('vendor', 'Vendor',),
        ('variant_title', 'Variant Title',),
        ('variant_compare_at_price', 'Variant Compare at Price',),
        ('variant_weight', 'Variant Weight',),
        ('variant_inventory', 'Variant Inventory',),
        ('is_price_reduced', 'Is Price Reduced'),
        ('variant_price', 'Variant Price'),
        ('tag', 'Tag'),
        ('product_metafield_definition', 'Product Metafield Definition'),
        ('product_taxonomy_node_id', 'Product Taxonomy Node Id')],
        string="Column")

    relation = fields.Selection([
        ('greater_than', 'greater_than'),
        ('less_than', 'less_than'),
        ('equals', 'equals'),
        ('not_equals', 'not_equals'),
        ('starts_with', 'starts_with'),
        ('ends_with', 'ends_with'),
        ('contains', 'contains'),
        ('not_contains', 'not_contains'),
        ('is_set', 'is_set'),
        ('is_not_set', 'is_not_set')], string="Relation")

    condition = fields.Char(string="Condition",
                            help="Enter values are either strings or numbers, "
                                 "depending on the relation value.")
    shopify_collection_id = fields.Many2one("shopify.product.collection",
                                            string="Collection")
