# -*- coding: utf-8 -*-
from odoo import api, models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ship_together = fields.Char()

