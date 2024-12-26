##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
from odoo import models


class ShopifyProductExport(models.TransientModel):
    _name = 'export.shopify.product'
    _description = 'Export Shopify Product Template'

    def export_shopify_product_template(self):
        shopify_prod_obj = self.env['shopify.product.template']
        for rec in self:
            active_ids = rec._context.get('active_ids')
            shopify_prod_search = shopify_prod_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_prod_tmpl_id", "in", ['', False])])
            # Add counter b'coz we can send only 2 request per second
            count = 1
            second = 5
            ctx = dict(self.env.context) or {}
            for product in shopify_prod_search:
                ctx.update({'queue_job_second': second})
                product.with_context(ctx).export_shopify()
                if count % 2 == 0:
                    time.sleep(0.5)
                count += 1
                second += 5