##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
from odoo import models, fields, api , _
from odoo.exceptions import ValidationError

class ProductExportReady(models.TransientModel):
    _name = "product.export.ready"
    _description = "Make Product Export Ready"


    shopify_config_ids = fields.Many2many("shopify.config", string="Shopify Config", help="Shopify Config for which product are export ready")


    def create_shopify_product_template(self, product_tmpl_id, shopify_config):
        ShopifyProductTemplate = self.env['shopify.product.template']
        vals = {'product_tmpl_id': product_tmpl_id.id,
                'shopify_published': product_tmpl_id.published_on_shopify,
                # 'shopify_published_scope': shopify_config.published_scope == 'web' and 'web' or None,
                'shopify_config_id': shopify_config.id,
                'product_type': product_tmpl_id.categ_id and product_tmpl_id.categ_id.id or False,
                # 'shopify_handle': product_tmpl_id.shopify_handle,
                'r_prod_tags': product_tmpl_id.prod_tags_ids and [(6, 0, product_tmpl_id.prod_tags_ids.ids)],
                'r_prov_tags': product_tmpl_id.province_tags_ids and [(6, 0, product_tmpl_id.province_tags_ids.ids)],
                'body_html':product_tmpl_id.description,
                # 'vendor':product_tmpl_id.brand_id.id if product_tmpl_id.brand_id else False,
                'name': product_tmpl_id.name,
                }
        return ShopifyProductTemplate.create(vals)

    def create_shopify_product_product(self, product_id, shopify_product_tmpl_id, shopify_config):
        ShopifyProductProduct = self.env['shopify.product.product']
        vals = {'product_variant_id': product_id.id,
                'shopify_product_template_id': shopify_product_tmpl_id.id,
                'lst_price': product_id.lst_price,
                'shopify_config_id': shopify_config.id,
                # 'shopify_product_name': product_id.name,
                # 'image_variant_1920': product_id.image_1920,
                }
        if shopify_product_tmpl_id.shopify_prod_tmpl_id:
            vals.update({'is_new_variant': True})
        shopify_product_product_id = ShopifyProductProduct.create(vals)

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

    def make_products_export_ready(self):
        ShopifyProductTemplate = self.env['shopify.product.template']
        ShopifyProductProduct = self.env['shopify.product.product']
        product_ids = self.env['product.product'].browse(self._context.get('active_ids'))
        for rec in product_ids:
            product_tmpl_id = rec.product_tmpl_id
            for shopify_config in self.shopify_config_ids:
                error_msg = self.check_product_sync(
                                shopify_config, rec)
                if error_msg:
                    raise ValidationError(_(error_msg))
                s_prod_tmpl_id = ShopifyProductTemplate.search([('product_tmpl_id', '=', product_tmpl_id.id),\
                                                                ('shopify_config_id', '=', shopify_config.id)])
                if not s_prod_tmpl_id:
                    s_prod_tmpl_id = self.create_shopify_product_template(product_tmpl_id, shopify_config)
                s_prod_prod_id = ShopifyProductProduct.search([('product_variant_id', '=', rec.id),\
                                                               ('shopify_config_id', '=', shopify_config.id)])
                if not s_prod_prod_id:
                    self.create_shopify_product_product(rec, s_prod_tmpl_id, shopify_config)