from odoo import http
from odoo.http import request


class ProductPriceEntryController(http.Controller):

    @http.route(['/fds_sale/show_product_price_entry'], type='json', auth="user", methods=['POST'])
    def product_price_entry(self, product_template_id, product_id, **kw):
        product_template = request.env['product.template'].browse(int(product_template_id))

        return request.env['ir.ui.view']._render_template("fds_sale.product_price_entry_modal", {
            'product_template': product_template,
            'product_id': product_id,
            'price_entry': 999.00
        })
