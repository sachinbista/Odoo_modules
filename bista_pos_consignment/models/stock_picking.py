# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _prepare_stock_move_vals(self,first_line,order_lines):
        res = super(StockPicking, self)._prepare_stock_move_vals(first_line,order_lines)
        res.update({
            'consignment_stock_move': first_line.consignment_move
        })
        return res