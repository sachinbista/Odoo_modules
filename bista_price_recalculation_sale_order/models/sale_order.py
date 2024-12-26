# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def recalculate_price(self):
        for line in self.mapped("order_line"):
            line._compute_price_unit()