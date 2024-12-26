# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_dropship = fields.Boolean(
        string="Is Dropship ?",
        default=False,
        readonly=False)
