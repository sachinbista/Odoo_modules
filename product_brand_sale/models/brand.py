# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string='Brand', help='Select a brand for this product')
    product_brand_family_id = fields.Many2one(comodel_name='product.brand.family', string='Family')


class BrandProduct(models.Model):
    _name = 'product.brand'

    name = fields.Char(String="Name")
    logo = fields.Binary()
    member_ids = fields.One2many('product.template', 'brand_id')
    product_count = fields.Char(String='Product Count',
                                compute='get_count_products', store=True)
    description = fields.Text('Description', translate=True)
    partner_id = fields.Many2one('res.partner', string='Partner', help='Select a partner for this brand if any.', ondelete='restrict')
    families = fields.One2many(comodel_name='product.brand.family', inverse_name='brand_id', string='Families')
    website_url = fields.Char(string='URL', compute='_get_website_url')
    active = fields.Boolean(default=True)
    website_published = fields.Boolean(default=True)
    is_brand_page = fields.Boolean(help="It will set the separate landing page for this brand")
    brand_page = fields.Many2one("website.page", string="Brand Page", help="Select the brand page which you want to set for this brand.")
    is_featured_brand = fields.Boolean()
    allow_in_brand_slider = fields.Boolean(help="You can set this brand in Brand carousel snippets.")

    def website_publish_button(self):
        return self.write({'website_published': not self.website_published})

    @api.depends('member_ids')
    def get_count_products(self):
        self.product_count = len(self.member_ids)

    @api.constrains('allow_in_brand_slider')
    def validate_brand_carousel(self):
        if not self.logo and self.allow_in_brand_slider:
            raise ValidationError(_("Please set the brand image before set this in carousel"))

    def set_brand_wizard(self):
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'product.brand.config',
            'name': "Product Brand Configuration",
            'view_mode': 'form',
            'target': 'new',
            'context': dict(default_brand_id=self.id),
        }
        return action


class ProductBrandFamily(models.Model):
    _name = 'product.brand.family'
    _inherit = ['website.searchable.mixin']
    _description = 'Product Family'

    name = fields.Char(string='Family Name', required=True)
    brand_id = fields.Many2one(comodel_name='product.brand', string='Brand', required=True)
    logo = fields.Binary(string='Family Image')
    website_id = fields.Many2one("website", string="Website", ondelete="restrict",help="Restrict publishing to this website.", index=True)
    is_published = fields.Boolean(string="Published", default=True)

    @api.model
    def _search_get_detail(self, website, order, options):
        search_fields = ['name']
        fetch_fields = ['id', 'name', 'brand_id']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'url', 'type': 'text', 'truncate': False},
        }
        return {
            'model': 'product.brand.family',
            'base_domain': [website.website_domain()+[('brand_id.active','=',True)]],
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-folder-o',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        brand_attribute_id = self.env['product.attribute'].sudo().search([('dr_is_brand','=',True)],limit=1)
        if brand_attribute_id:
            for data in results_data:
                brand_attribute_value = self.env['product.attribute.value'].sudo().search([('attribute_id.dr_is_brand', '=', True), ('name', '=', data['brand_id'][1])], limit=1)
                data['url'] = '/shop?attrib=%s-%s&brand_family=%s' % (brand_attribute_id.id,brand_attribute_value.id,data['id'])
        return results_data