# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    invoiced = fields.Boolean(compute='_check_if_invoiced', store=True)

    @api.depends("sale_line_id.qty_invoiced", "sale_line_id.product_uom_qty")
    def _check_if_invoiced(self):
        for move in self:
            invoiced = False
            if move.sale_line_id:
                if move.sale_line_id.product_uom_qty == move.sale_line_id.qty_invoiced:
                    invoiced = True
            move.invoiced = invoiced
