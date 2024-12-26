from odoo import http
from odoo.http import request


class PrintPDF(http.Controller):

    @http.route(
        '/print_label/<string:attachment_id>',
        type='http',
        auth='public',
        sitemap=False,
    )
    def print_label_pdf(self, attachment_id=None, **kwargs):
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        pdf_url = f'{base_url}/web/image/{attachment_id}'
        return request.render(
            "garazd_product_label_print.print_product_label_pdf_template",
            {
                'title': 'Print PDF',
                'pdf_url': pdf_url,
            },
        )
