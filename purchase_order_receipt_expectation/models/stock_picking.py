# -*- coding: utf-8 -*-

from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    receive_by_container = fields.Char(string='Receive by conatiner', copy=False)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    receipt_expectation = fields.Selection([('automatic', 'Automatic'), ('manual', 'Manual')],
                              string='Receipt Expectation')