##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
from odoo import models


class UpdateProductVariant(models.TransientModel):
    _name = 'update.shopify.variant'
    _description = 'Update Shopify Product Variant'

    def update_shopify_product_variant(self):
        """
           This method is updating the shopify products
           variants based on odoo on shopify.
           @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
       """
        shopify_product_variant_obj = self.env['shopify.product.product']
        for rec in self:
            active_ids = rec._context.get('active_ids')
            shopify_product_variants = shopify_product_variant_obj.search(
                [('id', 'in', active_ids),
                 ("shopify_product_id", "!=", False)])
            # Add counter b'coz we can send only 2 request per second
            count = 1
            for product in shopify_product_variants:
                product.update_shopify_variant()
                if count % 2 == 0:
                    time.sleep(0.5)
                count += 1
