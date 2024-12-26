##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
from odoo import models
from datetime import datetime, timedelta


class UpdateProductVariant(models.TransientModel):
    _name = 'update.shopify.variant'
    _description = 'Update Shopify Product Variant'

    def update_shopify_product_variant(self, shopify_product_variants=False):
        shopify_product_variant_obj = self.env['shopify.product.product']
        shopify_log_line_obj = self.env['shopify.log.line']

        # for rec in self:
        if not shopify_product_variants:
            active_ids = self._context.get('active_ids')
            shopify_product_variants = shopify_product_variant_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_product_id", "!=", False)], order='shopify_config_id asc')
        # Add counter b'coz we can send only 2 request per second
        count = 1
        parent_log_line_id = False
        for product in shopify_product_variants:
            log_line_vals = {}
            if not parent_log_line_id or parent_log_line_id.shopify_config_id.id != product.shopify_config_id.id:
                log_line_vals = {
                    'name': "Update Product Variant to Shopify",
                    'shopify_config_id': product.shopify_config_id.id,
                    'operation_type': 'update_product',
                }
                parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
            job_descr = ("Update Product:   %s") % (
                    product.product_variant_id.name or '')
            log_line_vals.update({
                'name': job_descr,
                'id_shopify': product.shopify_product_id,
                'parent_id': parent_log_line_id.id
            })
            log_line_id = shopify_log_line_obj.create(log_line_vals)
            eta = datetime.now() + timedelta(seconds=1)
            product.with_delay(
                description=job_descr, max_retries=5,
                eta=eta).update_shopify_variant(log_line_id)
            if count % 2 == 0:
                time.sleep(0.5)
            count += 1
