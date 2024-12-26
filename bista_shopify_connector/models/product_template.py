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
    export_status = fields.Selection([('no_export','No Export'),
                                      ('need_to_export','Need To Export'),
                                      ('exported','Exported')],
                                      string="Export Status",default='no_export')
    shopify_description = fields.Html('Description', translate=True)

    def open_shopify_variant(self):
        return {
            'name': _('Shopify Product Template'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'shopify.product.template',
            'context': self.env.context,
            'domain': [('id', 'in', self.shopify_product_template_ids and
                        self.shopify_product_template_ids.ids or [])]
        }

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

    @api.onchange('list_price')
    def onchange_list_price(self):
        if self.list_price:
            shopify_product_ids = self.env['shopify.product.product'].search([('product_template_id', '=' ,self._origin.id)])
            [shopify_product_id.update({'lst_price': self.list_price}) for shopify_product_id in shopify_product_ids]

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
            ready_to_update = False
            if not self._context.get('job_uuid'):
                if 'name' in vals:
                    ready_to_update = True
                if 'prod_tags_ids' in vals:
                    ready_to_update = True
                if 'province_tags_ids' in vals:
                    ready_to_update = True
            can_be_sold = vals.get('sale_ok') or rec.sale_ok
            can_be_purchased = vals.get('purchase_ok') or rec.purchase_ok
            shopify_published_list = []
            if not can_be_sold:
                shopify_product_templates = rec.shopify_product_template_ids
                for s_prod_temp in shopify_product_templates:
                    shopify_published_list.append(s_prod_temp.shopify_published)
                if True in shopify_published_list:
                    raise ValidationError(_("The product should be unpublished"
                                            " on shopify end as well!!"))
            shopi_tmpl_vals = {}
            # Boolean to define product updated and need to
            # sync with shopify
            if ready_to_update:
                shopi_tmpl_vals.update({'ready_to_update': ready_to_update})

            if vals.get('shopify_description'):
                shopi_tmpl_vals.update({'body_html': vals['shopify_description']})

            for shop_tmpl in rec.shopify_product_template_ids:
                coll_to_update = []
                if rec.prod_collection_ids.filtered(
                        lambda c: c.shopify_config_id.id ==
                                  shop_tmpl.shopify_config_id.id):
                    coll_to_update += [
                        (4, c_id.id) for c_id in
                        rec.prod_collection_ids.filtered(
                            lambda c: c.shopify_config_id.id ==
                                      shop_tmpl.shopify_config_id.id)]

                for shop_tmpl_col in shop_tmpl.shopify_prod_collection_ids:
                    if shop_tmpl_col.id not in rec.prod_collection_ids.ids:
                        coll_to_update.append((3, shop_tmpl_col.id))
                shopi_tmpl_vals.update({'shopify_prod_collection_ids':
                                            coll_to_update})
                if shopi_tmpl_vals:
                    shop_tmpl.write(shopi_tmpl_vals)
        return res

    @api.model
    def create(self, vals):
        rec = super(ProductTemplate, self).create(vals)
        shopify_config = self.env['shopify.config'].search([],limit=1)
        for r in rec:
            if r.type == 'service':
                r.invoice_policy = 'order'
            else:
                if shopify_config and shopify_config.is_create_product == True  and r.published_on_shopify == True:
                    r.invoice_policy = shopify_config.invoicing_policy
                else:
                    r.invoice_policy = 'order'
            shopi_tmpl_vals = {}
            if vals.get('shopify_description'):
                shopi_tmpl_vals.update({'body_html': vals['shopify_description']})

            for shop_tmpl in r.shopify_product_template_ids:
                coll_to_update = []
                if r.prod_collection_ids.filtered(
                        lambda c: c.shopify_config_id.id ==
                                  shop_tmpl.shopify_config_id.id):
                    coll_to_update += [
                        (4, c_id.id) for c_id in
                        r.prod_collection_ids.filtered(
                            lambda c: c.shopify_config_id.id ==
                                      shop_tmpl.shopify_config_id.id)]

                for shop_tmpl_col in shop_tmpl.shopify_prod_collection_ids:
                    if shop_tmpl_col.id not in r.prod_collection_ids.ids:
                        coll_to_update.append((3, shop_tmpl_col.id))
                shopi_tmpl_vals.update({'shopify_prod_collection_ids':
                                            coll_to_update})
                if shopi_tmpl_vals:
                    shop_tmpl.write(shopi_tmpl_vals)
        return rec

class ProductMultiImages(models.Model):
    _name = "product.multi.images"
    _description = "Multiple Images on Product"

    title = fields.Char(string='Title')
    description = fields.Char(string='Description')
    image = fields.Binary(string='Images')
    product_template_id = fields.Many2one('product.template', string='Product')
    shopify_image_id = fields.Char(string="Shopify Image Id")