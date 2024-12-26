##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
import traceback
from odoo import models


class ShopifyVariantExport(models.TransientModel):
    _name = 'export.shopify.variant'
    _description = 'Export Shopify Product Variant'

    def export_shopify_product_variant(self):
        shopify_prod_obj = self.env['shopify.product.product']
        for rec in self:
            active_ids = rec._context.get('active_ids')
            shopify_prod_search = shopify_prod_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_product_id", "in", ['', False])])
            # Add counter b'coz we can send only 2 request per second
            count = 1
            second = 5
            ctx = dict(self.env.context) or {}
            shopify_log_line_obj = self.env['shopify.log.line']
            log_line_vals = {
                'name': "Import Locations",
                'operation_type': 'import_refund',
            }
            parent_log_line_id = False
            try:
                for product in shopify_prod_search:
                    ctx.update({'queue_job_second': second})
                    if not parent_log_line_id:
                        log_line_vals.update({
                            'shopify_config_id': product.shopify_config_id.id,
                        })
                        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                    product.with_context(ctx).export_shopify_variant(parent_log_line_id)
                    if count % 2 == 0:
                        time.sleep(0.5)
                    count += 1
                    second += 5
                if parent_log_line_id:
                    parent_log_line_id.update({
                        'state': 'success',
                        'message': 'Operation Successful'
                    })
            except Exception as e:
                if parent_log_line_id:
                    parent_log_line_id.update({
                        'state': 'error',
                        'message': traceback.format_exc(),
                    })
