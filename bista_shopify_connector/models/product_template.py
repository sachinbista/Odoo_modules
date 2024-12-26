##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _, tools
from odoo.exceptions import AccessError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('product.product_category_all')

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
    export_ready_status = fields.Selection([('no_export', 'No Export'), ('need_to_export', 'Need To Export'),
                                            ('exported', 'Exported')], string='Export Ready Status', default='no_export')
    purchase_method = fields.Selection([
        ('purchase', 'On ordered quantities'),
        ('receive', 'On received quantities'),
    ], string="Control Policy", help="On ordered quantities: Control bills based on ordered quantities.\n"
        "On received quantities: Control bills based on received quantities.", default="purchase")
    detailed_type = fields.Selection(selection_add=[
        ('product', 'Storable Product')
    ], tracking=True, ondelete={'product': 'set consu'}, default="product")
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=_get_default_category_id, group_expand='_read_group_categ_id',
        required=True, tracking=True)
    shoipify_product_template_id = fields.Many2one(
        'shopify.product.template', string="Shopify Product", compute='get_shopify_product')

    @api.depends('shoipify_product_template_id')
    def get_shopify_product(self):
        shopify_product = self.env['shopify.product.template'].search(
            [('product_tmpl_id', '=', self.id)], limit=1)
        self.shoipify_product_template_id = shopify_product.id if shopify_product else False

    @api.depends('type')
    def _compute_tracking(self):
        self.filtered(
            lambda t: not t.tracking or t.type == 'consu' and t.tracking != 'none'
        ).tracking = 'lot'

    # @api.constrains('default_code')
    # def _check_default_code_uniq_template(self):
    #     """
    #     Prevent the default code duplication when creating product template
    #     """
    #     for rec in self:
    #         if rec.default_code:
    #             search_product_count = self.search_count(
    #                 [('default_code', '=', rec.default_code), ('id', '!=', rec.id)])
    #             if search_product_count > 1:
    #                 raise ValidationError(_(f'SKU Code "{rec.default_code}" must be unique per Product.'))
    #     return True

    @api.onchange('list_price')
    def onchange_list_price(self):
        if self.list_price:
            shopify_product_ids = self.env['shopify.product.product'].search(
                [('product_template_id', '=', self._origin.id)])
            [shopify_product_id.update({'lst_price': self.list_price})
             for shopify_product_id in shopify_product_ids]

    def write(self, vals):
        """
            Restrict a user from making can_be_sold and can_be_purchased false if a
            product is exported on Shopify. If we import SO who's is can be sold
            and can be purchased then it'll create an issue for creating a sales
            order or purchase order.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        # vals['invoice_policy'] = 'order'
        res = super(ProductTemplate, self).write(vals)
        for rec in self:
            can_be_sold = vals.get('sale_ok') or rec.sale_ok
            can_be_purchased = vals.get('purchase_ok') or rec.purchase_ok
            shopify_published_list = []
            if not can_be_sold or not can_be_purchased:
                shopify_product_templates = rec.shopify_product_template_ids
                for s_prod_temp in shopify_product_templates:
                    shopify_published_list.append(
                        s_prod_temp.shopify_published)
                # if True in shopify_published_list:
                #     raise ValidationError(_("The product should be unpublished"
                #                             " on shopify end as well!!"))
        return res

    @api.model_create_multi
    def create(self, vals):
        """
            Assigned default values for product at time of creation.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        rec = super(ProductTemplate, self).create(vals)
        for line in rec:
            if line.shopify_product_template_ids:
                line.write({'invoice_policy': 'order',
                           'tracking': 'serial', 'detailed_type': 'product'})
        return rec


class ProductMultiImages(models.Model):
    _name = "product.multi.images"
    _description = "Multiple Images on Product"

    title = fields.Char(string='Title')
    description = fields.Char(string='Description')
    image = fields.Binary(string='Images')
    product_template_id = fields.Many2one('product.template', string='Product')
    shopify_image_id = fields.Char(string="Shopify Image Id")
