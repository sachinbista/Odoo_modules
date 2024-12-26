import logging
from odoo import fields, models
_logger = logging.getLogger(__name__)


class QuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    package_height = fields.Float('Height', help="Package Height")
    package_weight = fields.Float('Weight', help="Package Weight")
    package_depth = fields.Float('Depth', help='Package Weight')

    def create_scrap_oders(self):
        """Create scrap order for package_product_id."""
        values = []
        for package in self.filtered(lambda p: p.package_type_id.package_product_id):
            values.append(package._prepare_scrap_order_vals())
        
        if values:
            scrap_orders = self.env['stock.scrap'].create(values)
            scrap_orders.do_scrap()
            return scrap_orders
        return False

    def _prepare_scrap_order_vals(self):
        package_product = self.package_type_id.package_product_id
        return {
            'origin': self.name,
            'product_id': package_product.id,
            'product_uom_id': package_product.uom_id.id,
            'scrap_qty': 1.0
        }
