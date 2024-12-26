import logging
from odoo import fields, models
_logger = logging.getLogger(__name__)


class StockPackageType(models.Model):
    _inherit = 'stock.package.type'

    package_product_id = fields.Many2one('product.product', string='Product')
