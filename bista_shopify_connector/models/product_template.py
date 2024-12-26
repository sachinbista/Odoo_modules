##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_product_template_ids = fields.One2many(
        "shopify.product.template",
        'product_tmpl_id',
        "Shopify Product Templates",
        help="Select Shopify Product Templates",
        tracking=True)
    prod_tags_ids = fields.Many2many(
        "shopify.product.tags",
        'shopify_prod_tags_template_rel',
        'prod_tag_id',
        'product_template_id',
        "Prod. Tags",
        help="Enter Prod. Tags",
        tracking=True,
        domain=[('is_province', '=', False)])
    province_tags_ids = fields.Many2many(
        "shopify.product.tags",
        'shopify_province_tags_template_rel',
        'province_tag_id',
        'product_template_id',
        "Province Tags",
        help="Enter Province Tags",
        tracking=True,
        domain=[('is_province', '=', True)])

    published_on_shopify = fields.Boolean(
        "Published on Shopify",
        help="Published on Shopify",
        tracking=True,
        copy=False)
    prod_collection_ids = fields.Many2many('shopify.product.collection',
                                           'shopify_collection_template_rel',
                                           'collection_id',
                                           'prod_template_id',
                                           string='Collections'
                                           )
    product_multi_images = fields.One2many('product.multi.images',
                                           'product_template_id',
                                           'Product Multiple Images')

    @api.constrains('default_code')
    def _check_default_code_uniq_template(self):
        """
        Prevent the default code duplication when creating product template
        """
        for rec in self:
            if rec.default_code:
                search_product_count = self.search_count(
                    [('default_code', '=', rec.default_code)])
                if search_product_count > 1:
                    raise ValidationError(_('Default Code must be unique per '
                                            'Product!'))
        return True

    def write(self, vals):
        """
        Restrict a user from making can_be_sold and can_be_purchased false if a
        product is exported on Shopify. If we import SO who's is can be sold
        and can be purchased then it'll create an issue for creating a sales
        order or purchase order.
        """
        if vals.get('type') == 'service':
            vals['invoice_policy'] = 'order'
        res = super(ProductTemplate, self).write(vals)
        for rec in self:
            can_be_sold = vals.get('sale_ok') or rec.sale_ok
            can_be_purchased = vals.get('purchase_ok') or rec.purchase_ok
            shopify_published_list = []
            if not can_be_sold or not can_be_purchased:
                shopify_product_templates = rec.shopify_product_template_ids
                for s_prod_temp in shopify_product_templates:
                    shopify_published_list.append(s_prod_temp.shopify_published)
                if True in shopify_published_list:
                    raise ValidationError(_("The product should be unpublished"
                                            " on shopify end as well!!"))
        return res

    @api.model_create_multi
    def create(self, vals):
        rec = super(ProductTemplate, self).create(vals)
        for r in rec:
            if r.type == 'service':
                r.invoice_policy = 'order'
        return rec


class ProductMultiImages(models.Model):
    _name = "product.multi.images"
    _description = "Multiple Images on Product"

    title = fields.Char(string='Title')
    description = fields.Char(string='Description')
    image = fields.Binary(string='Images')
    product_template_id = fields.Many2one('product.template', string='Product')
    shopify_image_id = fields.Char(string="Shopify Image Id")