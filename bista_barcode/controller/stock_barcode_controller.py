from odoo import http
from odoo.http import request
from odoo.modules.module import get_resource_path
from odoo.tools.misc import file_open
from odoo.tools import pdf, split_every
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class StockBarcodeControllerInherit(StockBarcodeController):

    def _get_groups_data(self):
        ret = super(StockBarcodeControllerInherit, self)._get_groups_data() or {}
        ret.update({
            'group_stock_manager': request.env.user.has_group('stock.group_stock_manager'),
        })
        return ret