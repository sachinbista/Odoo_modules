from odoo import http
from odoo.http import request
from odoo.osv import expression

from odoo.addons.website_sale.controllers.main import WebsiteSale
from werkzeug.datastructures import ImmutableOrderedMultiDict


class BistaWebsiteSale(WebsiteSale):

    def get_pav_ids(self, attrib_list=[], category_id=False):
        """
        product attribute value ids based on attribute ids and category id
        return dictionary with attribute id as key and list of product attribute value ids as value
        """
        query = """
            SELECT DISTINCT
                ptav.product_attribute_value_id, ptav.attribute_id
            FROM
                product_template_attribute_value ptav
                JOIN product_public_category_product_template_rel pbc
                ON pbc.product_template_id=ptav.product_tmpl_id
            WHERE
                ptav.attribute_id = %s and ptav.ptav_active=true
        """
        if category_id:
            query += " AND pbc.product_public_category_id = %s"
            request.env.cr.execute(query, (tuple(attrib_list), category_id))
        else:
            request.env.cr.execute(query, (tuple(attrib_list),))
        res = request.env.cr.fetchall()
        result = {}
        for value in res:
            if value[1] not in result:
                result[value[1]] = []
            result[value[1]].append(value[0])
        return result

    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        attrib_list = request.httprequest.args.getlist('attrib')
        request_args = request.httprequest.args.copy()
        attrib_view_all_list = request.httprequest.args.getlist('attribute')
        if attrib_view_all_list and not attrib_list:
            attribute_list = [int(a) for a in attrib_view_all_list if a.strip().isdigit()]
            attrib_value_ids = self.get_pav_ids(attribute_list, category_id=category.id if category else False)
            for value_id in attrib_value_ids:
                # update request.httprequest.args with attrib value ids attrib=attribute_id-value_id
                print(value_id)
                for attrib_value_id in attrib_value_ids[value_id]:
                    request_args.add('attrib', f"{value_id}-{attrib_value_id}")
            request_args.pop('attribute')
            request.httprequest.args = ImmutableOrderedMultiDict(request_args)
        response = super().shop(page=page, category=category, search=search, min_price=min_price, max_price=max_price, ppg=ppg, **post)
        return response
    
    @http.route('/recently-purchased', type='http', auth="public", website=True)
    def recently_purchased(self, **post):
        DynamicFilter = request.env['website.snippet.filter']
        website = request.env['website'].get_current_website()
        limit = 20
        domain = expression.AND([
            [('website_published', '=', True)],
            website.website_domain(),
            [('company_id', 'in', [False, website.company_id.id])]
        ])
        products = DynamicFilter._get_products_latest_sold(website, limit, domain, request.env.context)
        qcontext = {
            'products': products
        }
        return request.render('website_configuration.recently_purchased_page', qcontext)
