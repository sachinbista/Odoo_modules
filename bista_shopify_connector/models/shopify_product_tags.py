##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class ShopifyProductTags(models.Model):
    _name = 'shopify.product.tags'
    _description = 'Shopify Product Tags'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Name', help='Enter Name', tracking=True,
                       required=True)
    shopify_config_ids = fields.Many2many('shopify.config',
                                          string='Shopify Configurations',
                                          help='Enter Shopify Configurations',
                                          tracking=True, required=True)
    color = fields.Integer(string='Color', help='Enter the Color',
                           tracking=True)
    is_province = fields.Boolean(string='Province', help='Province Yes/No',
                                 tracking=True)
    active = fields.Boolean(string='Active', help='Active Yes/No', tracking=True,
                            default=True)
