##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _


class ShopifyProductMapping(models.Model):
    _name = 'shopify.product.mapping'
    _description = 'Shopify Product Mapping'
    _rec_name = 'product_variant_id'

    shopiy_product_name = fields.Char(string="Shopify Product Name",
                                      help="Enter Shopify Product Name",
                                      required=True, copy=False)
    product_variant_id = fields.Many2one("product.product", "Product Variant",
                                         help="Enter Product Variant",
                                         required=True, copy=False)
