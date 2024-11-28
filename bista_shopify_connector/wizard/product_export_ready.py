##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import threading
import time
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductExportReady(models.TransientModel):
    _name = "product.export.ready"
    _description = "Make Product Export Ready"

    def _get_default_shopify_configuration(self):
        shopify_config_id = self.env['shopify.config'].search(
                [('state', '=', 'success')], limit=1)
        return shopify_config_id

    shopify_config_ids = fields.Many2many(
        "shopify.config", string="Shopify Config", help="Shopify Config for which product are export ready", default=_get_default_shopify_configuration)

    def create_shopify_product_template(self, product_tmpl_id, shopify_config):
        ShopifyProductTemplate = self.env['shopify.product.template']
        vals = {'product_tmpl_id': product_tmpl_id.id,
                'shopify_published': product_tmpl_id.published_on_shopify,
                'shopify_config_id': shopify_config.id,
                'product_type': product_tmpl_id.categ_id and product_tmpl_id.categ_id.id or False,
                'r_prod_tags': product_tmpl_id.prod_tags_ids and [(6, 0, product_tmpl_id.prod_tags_ids.ids)],
                'r_prov_tags': product_tmpl_id.province_tags_ids and [(6, 0, product_tmpl_id.province_tags_ids.ids)],
                'body_html': product_tmpl_id.description,
                'name': product_tmpl_id.name,
                }
        return ShopifyProductTemplate.create(vals)

    def create_shopify_product_product(self, product_id, shopify_product_tmpl_id, shopify_config):
        ShopifyProductProduct = self.env['shopify.product.product']
        vals = {'product_variant_id': product_id.id,
                'shopify_product_template_id': shopify_product_tmpl_id.id,
                'lst_price': product_id.lst_price,
                'shopify_config_id': shopify_config.id,
                }
        shopify_product_product_id = ShopifyProductProduct.create(vals)
        if shopify_product_product_id:
            product_id.product_tmpl_id.write(
                {'export_ready_status': 'exported'})

    def make_products_export_ready(self):
        ShopifyProductTemplate = self.env['shopify.product.template']
        ShopifyProductProduct = self.env['shopify.product.product']
        product_ids = self.env['product.product'].browse(self._context.get('active_ids'))
        for rec in product_ids:
            product_tmpl_id = rec.product_tmpl_id
            for shopify_config in self.shopify_config_ids:
                if shopify_config.sync_product == 'sku' and not rec.default_code:
                    raise ValidationError(
                        _('Please add "Default Code" for product %s!') % rec.name)
                elif shopify_config.sync_product == 'barcode' and not rec.barcode:
                    raise ValidationError(
                        _('Please add "Barcode" for all product %s!') % rec.name)
                elif shopify_config.sync_product == 'sku_barcode' and (not rec.barcode or not rec.default_code):
                    raise ValidationError(
                        _('Please add "Barcode" or "Default Code" for product %s!') % rec.name)
                s_prod_tmpl_id = ShopifyProductTemplate.search([('product_tmpl_id', '=', product_tmpl_id.id), \
                                                                ('shopify_config_id', '=', shopify_config.id)])
                if not s_prod_tmpl_id:
                    s_prod_tmpl_id = self.create_shopify_product_template(product_tmpl_id, shopify_config)
                s_prod_prod_id = ShopifyProductProduct.search([('product_variant_id', '=', rec.id), \
                                                               ('shopify_config_id', '=', shopify_config.id)])
                if not s_prod_prod_id:
                    self.create_shopify_product_product(rec, s_prod_tmpl_id, shopify_config)

    def check_product_sync(self, shopify_config, product):
        message = ""
        if shopify_config.sync_product == 'sku' and not product.default_code:
            message = (
                'Please add "Default Code" for product %s!') % product.name
        elif shopify_config.sync_product == 'barcode' and not product.barcode:
            message = (
                'Please add "Barcode" for all product %s!') % product.name
        elif shopify_config.sync_product == 'sku_barcode' and (not product.barcode and not product.default_code):
            message = (
                'Please add "Barcode" or "Default Code" for product %s!') % product.name
        return message

    def stock_check_product_sync(self, shopify_config, product):
        message = ""
        if shopify_config.sync_product == 'sku' and not product.default_code:
            message = (
                'Please add "Internal Reference" for product %s!') % product.name
        elif shopify_config.sync_product == 'barcode' and not product.barcode:
            message = (
                'Please add "Barcode" for all product %s!') % product.name
        elif shopify_config.sync_product == 'sku_barcode' and (not product.barcode and not product.default_code):
            message = (
                'Please add Internal Reference or "Barcode" for product %s!') % product.name
        return message

    def create_export_shopi_template(self, product_tmpl_id, shopify_config):
        """
            Using this method we are creating the records in "shopify.product.template"
        """
        ShopifyProductTemplate = self.env['shopify.product.template']
        vals = {'product_tmpl_id': product_tmpl_id.id,
                'shopify_published': product_tmpl_id.published_on_shopify,
                'shopify_config_id': shopify_config.id,
                'product_type': product_tmpl_id.categ_id and product_tmpl_id.categ_id.id or False,
                'r_prod_tags': product_tmpl_id.prod_tags_ids and [(6, 0, product_tmpl_id.prod_tags_ids.ids)],
                'r_prov_tags': product_tmpl_id.province_tags_ids and [(6, 0, product_tmpl_id.province_tags_ids.ids)],
                'body_html': product_tmpl_id.description,
                'name': product_tmpl_id.name,
                }
        return ShopifyProductTemplate.create(vals)

    def create_export_shopi_variant(self, product_id, shopify_product_tmpl_id, shopify_config):
        """
            Using this method we are creating the records in "shopify.product.product"
        """
        ShopifyProductProduct = self.env['shopify.product.product']
        vals = {'product_variant_id': product_id.id,
                'shopify_product_template_id': shopify_product_tmpl_id.id,
                'lst_price': product_id.lst_price,
                'shopify_config_id': shopify_config.id,
                }
        shopify_product_product_id = ShopifyProductProduct.create(vals)
        if shopify_product_product_id:
            product_id.product_tmpl_id.write(
                {'export_ready_status': 'exported'})
        return shopify_product_product_id

    def send_product_to_shopify(self):
        threaded_calculation = threading.Thread(target=self._send_product_to_shopify, args=())
        threaded_calculation.start()
        return {
            'name': _('Send Product Items Log'),
            'type': 'ir.actions.act_window',
            'view_type': 'tree',
            'view_mode': 'tree',
            'views': [[self.env.ref('bista_shopify_connector.view_send_prod_to_shopify_log_tree').id, 'tree']],
            'res_model': 'send.to.shopify.log',
        }
    
    def product_batch_split(self,product_input_list, product_batch_size):
        return [product_input_list[data:data + product_batch_size] for data in range(0, len(product_input_list), product_batch_size)]

