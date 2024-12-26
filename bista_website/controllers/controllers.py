# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class BistaWebsiteSale(WebsiteSale):
    
    def get_parent_public_categ_ids_pav(self, pav_list):
        """
        return parent public category ids based on product attribute value ids
        """
        query = """
        SELECT DISTINCT
                pbc.product_public_category_id, ppc.parent_id
            FROM
                product_public_category_product_template_rel pbc
                JOIN product_template_attribute_value ptav 
                ON pbc.product_template_id=ptav.product_tmpl_id
				JOIN product_public_category ppc
				ON ppc.id = pbc.product_public_category_id
            WHERE
                ptav.product_attribute_value_id IN %s;
        """
        request.env.cr.execute(query, (tuple(pav_list),))
        res = request.env.cr.fetchall()
        parent_category_ids = []
        for query_result in res:
            parent_id = query_result[1]
            if parent_id:
                parent_category_ids.append(parent_id)
            else:
                parent_category_ids.append(query_result[0])
        return list(set(parent_category_ids))
    
    def get_public_categ_ids_pav(self, pav_list):
        """
        return public category ids based on product attribute value ids
        """
        query = """
            SELECT DISTINCT
                pbc.product_public_category_id
            FROM
                product_public_category_product_template_rel pbc
                JOIN product_template_attribute_value ptav 
                ON pbc.product_template_id=ptav.product_tmpl_id
            WHERE
                ptav.product_attribute_value_id IN %s
        """
        request.env.cr.execute(query, (tuple(pav_list),))
        res = request.env.cr.fetchall()
        return [r[0] for r in res]

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        res = super(BistaWebsiteSale, self).product(product, category, search, **kwargs)

        lot_serial_list = request.env['stock.lot'].sudo().search([
            ('product_id', 'in', product.product_variant_ids.ids),
            ('company_id', '=', request.website.company_id.id),
            ('available_quantity', '>', 0)
        ])
        res.qcontext.update({
            'lot_serial_list': lot_serial_list,
        })

        return res
    
    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        response = super().shop(page=page, category=category, search=search, min_price=min_price, max_price=max_price, ppg=ppg, **post)
        Category = request.env['product.public.category']
        if not category:
            attrib_list = request.httprequest.args.getlist('attrib')
            attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
            pav_list = [v[1] for v in attrib_values]
            if attrib_list:
                public_categ_ids = self.get_parent_public_categ_ids_pav(pav_list)
                response.qcontext['categories'] = Category.browse(public_categ_ids)
        return response

class BistaWebsiteSaleCart(http.Controller):

    @http.route(['/add/gift/message/product'], type='json', auth="public", methods=['POST'], website=True)
    def add_gift_message_product(self, gift_message=False, is_update=0):
        """
        Adding gift product to the cart 
        """
        gift_product = request.env['ir.model.data'].sudo().search([('name','=','product_gift_card_message')])
        sale_order = request.website.sale_get_order()
        gift_product=request.env['product.template'].sudo().browse(gift_product.sudo().res_id)
        if is_update == 0:
            request.env['sale.order.line'].sudo().create({
                'product_template_id':gift_product.id,
                'product_id': gift_product.product_variant_id.id,
                'product_uom_qty': 1,
                'name': gift_message,
                'order_id': sale_order.id,
                'is_gift_product': True
            })
        else:
            is_gift_product_line = sale_order.order_line.filtered(lambda so: so.is_gift_product)
            is_gift_product_line.name = gift_message
        return
            