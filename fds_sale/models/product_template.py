from odoo import models, fields

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_both_MTO_BUY = fields.Boolean(
        compute='_compute_is_both_MTO_BUY'
    )

    def _compute_is_both_MTO_BUY(self):
        route_MTO_BUY = self.env.ref('stock.route_warehouse0_mto') +\
            self.env.ref('purchase_stock.route_warehouse0_buy')
        for product_template in self:
            product_template.is_both_MTO_BUY = all(route in product_template.route_ids for route in route_MTO_BUY)

    def get_single_product_variant(self):
        self.ensure_one()
        res = super(ProductTemplate, self).get_single_product_variant()
        res.update({'is_both_MTO_BUY': self.is_both_MTO_BUY})
        return res
