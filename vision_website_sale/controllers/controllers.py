# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class WebsiteSaleInh(WebsiteSale):

    def _prepare_product_values(self, product, category, search, **kwargs):
        res = super(WebsiteSaleInh, self)._prepare_product_values(product,
                                                                  category=category,
                                                                  search=search,
                                                                  kwargs=kwargs)

        otherAttributes = []
        for line in product.attribute_line_ids.filtered(lambda p: p.attribute_id.attribute_type != 'size'):
            if len(line.value_ids) <= 1:
                continue 
            otherAttributes.append(line.attribute_id.id) 

        res['otherAttributes'] = otherAttributes
        res['sizeAttribute'] = product.attribute_line_ids.mapped('attribute_id').filtered(lambda attr: attr.attribute_type == 'size').id
        return res

    @http.route(['/product/getServices'], type='json', auth="public",
                methods=['POST'],
                website=True,
                csrf=False)
    def get_product_services(self, product_id, other_attributes=False, **kw):
        product_template = request.env['product.template'].sudo().browse(int(product_id))
        service_ids = product_template.get_compatible_services(other_attributes)
        return service_ids

    @http.route(['/product/getVariants'], type='json', auth="public",
                methods=['POST'],
                website=True,
                csrf=False)
    def get_product_variants(self, product_id, service_id=False, other_attributes=False, **kw):
        other_attributes = [int(attribute) for attribute in other_attributes]

        if service_id:
            product_template = request.env['product.product'].sudo().browse(int(service_id))
            compatible_variants = product_template.allowed_products
        else:
            compatible_variants = request.env['product.template'].sudo().browse(int(product_id)).product_variant_ids
        
        if other_attributes:
            variant_ids = compatible_variants.filtered(
                lambda p: p.product_tmpl_id.id == int(product_id)
                          and all(attribute in p.product_template_variant_value_ids.ids for attribute in other_attributes))
        else:
            variant_ids = compatible_variants.filtered(
                lambda p: p.product_tmpl_id.id == int(product_id))
        

        matrix = {}
        print("Variants ", variant_ids)
        for product in variant_ids:
            size_id = product.product_template_variant_value_ids.filtered(
                lambda v: v.attribute_id.attribute_type == 'size')
            if not size_id:
                continue
            if len(size_id) > 1:
                size_id = size_id[0]
            matrix[size_id.name] = product.id

        return matrix

    def _get_attribute_key(self, attribute):
        return {'id': attribute.id, 'display_name': attribute.display_name}
