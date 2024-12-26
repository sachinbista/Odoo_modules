from odoo import http
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.tools.misc import file_open
from odoo.tools import pdf, split_every
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class StockBarcodeControllerInherit(StockBarcodeController):

    @http.route('/stock_barcode/print_inventory_commands', type='http', auth='user')
    def print_barcode_commands(self):
        if not request.env.user.has_group('stock.group_stock_user'):
            return request.not_found()

        barcode_pdfs = []
        # get fixed command barcodes
        file_path = get_resource_path('bista_zpl_labels', 'static/img', 'barcodes_actions.pdf')
        with file_open(file_path, "rb") as commands_file:
            barcode_pdfs.append(commands_file.read())

        merged_pdf = pdf.merge_pdf(barcode_pdfs)

        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(merged_pdf))
        ]

        return request.make_response(merged_pdf, headers=pdfhttpheaders)
