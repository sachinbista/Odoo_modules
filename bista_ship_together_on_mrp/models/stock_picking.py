# -*- coding: utf-8 -*-
from odoo import api, models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ship_together = fields.Char(related="sale_id.ship_together", store=True)
