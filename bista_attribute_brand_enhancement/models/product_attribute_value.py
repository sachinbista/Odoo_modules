# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _



class  ProductAttributeValue(models.Model):
    _name = 'product.attribute.value'
    _inherit = ['product.attribute.value', 'website.searchable.mixin']

    brand_id = fields.Many2one('product.brand' ,String="Brand")
    website_id = fields.Many2one("website", string="Website", ondelete="restrict", help="Restrict publishing to this website.", index=True)
    is_published = fields.Boolean(string="Published", default=True)

    @api.model
    def _search_get_detail(self, website, order, options):
        search_fields = ['name']
        fetch_fields = ['id', 'name']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'url', 'type': 'text', 'truncate': False},
        }

        return {
            'model': 'product.attribute.value',
            'base_domain': [website.website_domain()],
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
                data['url'] = '/shop?attrib=%s-%s' % (brand_attribute_id.id,data['id'])
        return results_data






