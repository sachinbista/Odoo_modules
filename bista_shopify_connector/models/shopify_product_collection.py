##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, _
from .. import shopify
from odoo.exceptions import AccessError, ValidationError, UserError
import urllib
import base64
from datetime import time
import logging
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
                                        string='Shopify Config', copy=False)
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

    def create_update_collection(self, data, type, shopify_config):
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
                    condition_dict = conditions.attributes
                    if isinstance(condition_dict, dict):
                        condition_vals.append((0, 0, {
                            'column': condition_dict.get('column'),
                            'relation': condition_dict.get('relation'),
                            'condition': condition_dict.get('condition')}))
                collection_vals.update(
                    {'collection_condition_ids': condition_vals,
                     'is_disjunctive': disjunctive})
        image_data = data.get('image', {})
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
            self.create(collection_vals)

    def shopify_import_product_collection(self, shopify_config,
                                          list_of_collections=[], since_id=0):
        error_log_env = self.env['shopify.error.log']
        shopify_id = 0
        try:
            shopify_config.check_connection()
            smart_collections = shopify.SmartCollection().find(limit=250,
                                                               since_id=since_id)
            for smart_collect in smart_collections:
                list_of_collections.append(smart_collect.id)
                smart_collect_data = smart_collect.attributes
                self.create_update_collection(smart_collect_data, 'automated', shopify_config)

            collections = shopify.CustomCollection().find(limit=250,
                                                          since_id=since_id)
            for collection in collections:
                list_of_collections.append(collection.id)
                data = collection.attributes
                self.create_update_collection(data, 'manual', shopify_config)

            if len(list_of_collections) >= 250:
                self.shopify_import_product_collection(
                    shopify_config=shopify_config,
                    list_of_collections=list_of_collections, since_id=shopify_id)
            else:
                self.deactive_collection(list_of_collections)
        except Exception as e:
            if hasattr(e, "response"):
                if e and e.response.code == 429 and e.response.msg == "Too Many Requests":
                    time.sleep(5)
                    self.shopify_import_product_collection(shopify_config)
            error_msg = "Facing a problems while importing Collections!: %s" % e
            shopify_log_id = error_log_env.create_update_log(
                shopify_config_id=shopify_config,
                operation_type='import_collection')
            error_log_env.create_update_log(
                shop_error_log_id=shopify_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': error_msg}]})
            _logger.error(_(error_msg))
            # raise AccessError(_(error_msg))

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

    def shopify_export_product_collection(self, shopify_config):
        error_log_env = self.env['shopify.error.log']
        shopify_config.check_connection()
        try:
            for collection in self.search([('shopify_published', '=', False)]):
                if collection.type == 'manual':
                    new_collection = shopify.CustomCollection()
                    collection_vals = collection.prepare_collection_vals()
                else:
                    new_collection = shopify.SmartCollection()
                    collection_vals = collection.prepare_collection_vals()

                result = new_collection.create(collection_vals)
                if not result.id:
                    error_msg = "Getting response '%s' on Export Collection: Please review Conditions and Details." % result
                    shopify_log_id = error_log_env.create_update_log(
                        shopify_config_id=shopify_config,
                        operation_type='export_collection')
                    error_log_env.create_update_log(
                        shop_error_log_id=shopify_log_id,
                        shopify_log_line_dict={'error': [
                            {'error_message': error_msg}]})
                    continue
                collection.update({'shopify_id': result.id,
                                   'shopify_published': True,
                                   'shopify_config_id': shopify_config.id})

        except Exception as e:
            error_msg = "Error on Export Manually/Automated Collection: %s" % e
            shopify_log_id = error_log_env.create_update_log(
                shopify_config_id=shopify_config,
                operation_type='export_collection')
            error_log_env.create_update_log(
                shop_error_log_id=shopify_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': error_msg}]})
            _logger.error(_(error_msg))
            # raise ValidationError(
            #     _("Error on Export Manually/Automated Collection: {}".format(e)))

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
        return new_collection

    def update_collection_in_shopify(self):
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
        except Exception as e:
            raise ValidationError(
                _("Error on Update Manually/Automated Collection: {}".format(e)))

    def shopify_update_product_collection(self, shopify_config):
        shopify_config.check_connection()
        try:
            for collection in self.search([('shopify_published', '=', True),
                                           ('shopify_id', '!=', False)]):
                if collection.type == 'manual':
                    update_collection = shopify.CustomCollection().find(
                        collection.shopify_id)
                    update_collection = collection.prepare_update_collection_vals(
                        update_collection)
                else:
                    if not collection.collection_condition_ids:
                        raise UserError(_(
                                "Please Add conditions in %s" % collection.name))
                    update_collection = shopify.SmartCollection().find(
                        collection.shopify_id)
                    update_collection = collection.prepare_update_collection_vals(
                        update_collection)
                update_collection.save()

        except Exception as e:
            raise ValidationError(
                _("Error on Update Manually/Automated Collections: {}".format(e)))


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
        ('variant_price', 'Variant Price'),
        ('tag', 'Tag')], string="Column")
    relation = fields.Selection([
        ('greater_than', 'greater_than'),
        ('less_than', 'less_than'),
        ('equals', 'equals'),
        ('not_equals', 'not_equals'),
        ('starts_with', 'starts_with'),
        ('ends_with', 'ends_with'),
        ('contains', 'contains'),
        ('not_contains', 'not_contains')], string="Relation")
    condition = fields.Char(string="Condition",
                            help="Enter values are either strings or numbers, "
                                 "depending on the relation value.")
    shopify_collection_id = fields.Many2one("shopify.product.collection",
                                            string="Collection")
