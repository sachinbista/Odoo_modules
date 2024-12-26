##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
from odoo import models
from datetime import datetime, timedelta



class ShopifyProductUpdate(models.TransientModel):
    _name = 'update.shopify.product'
    _description = 'Update Shopify Product Template'

    def update_shopify_product_template(self, shopify_prod_search=False):
        shopify_prod_obj = self.env['shopify.product.template']
        # for rec in self:
        if not shopify_prod_search:
            active_ids = self._context.get('active_ids')
            shopify_prod_search = shopify_prod_obj.sudo().search(
                [('id', 'in', active_ids),
                 ("shopify_prod_tmpl_id", "!=", False)])
        # Add counter b'coz we can send only 2 request per second
        # count = 1
        seconds = 5
        ctx = dict(self.env.context) or {}
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {}
        parent_log_line_id = False
        shopify_initial_id = False
        for product in shopify_prod_search:
            # if not shopify_initial_id:
            if shopify_initial_id != product.shopify_config_id:
                shopify_initial_id = product.shopify_config_id
                log_line_vals.update({
                    'shopify_config_id': shopify_initial_id.id,
                })
                parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                if ctx.get('export_product_template_info'):
                    parent_log_line_id.update({
                        'name': "Update products",
                        'operation_type': 'update_product',
                    })
                elif ctx.get('import_product_template_info'):
                    parent_log_line_id.update({
                        'name': "Import products",
                        'operation_type': 'import_product',
                    })

            if ctx.get('export_product_template_info'):
                eta = datetime.now() + timedelta(seconds=seconds)
                product.with_delay(
                    description="Update Products", max_retries=5, eta=eta).update_product_shopify(parent_log_line_id)
            elif ctx.get('import_product_template_info'):
                eta = datetime.now() + timedelta(seconds=seconds)
                product.with_delay(
                    description="Import Product", max_retries=5, eta=eta).update_shopify_product(parent_log_line_id)

            seconds += 2
            # if count % 2 == 0:
            #     time.sleep(0.5)
            # count += 1
            # second += 5
