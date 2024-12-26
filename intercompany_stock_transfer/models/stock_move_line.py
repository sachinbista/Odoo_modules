# -*- coding: utf-8 -*-

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _log_message(self, record, move, template, vals):
        if self._context.get('tracking_disable', False):
            return True
        else:
            return super(StockMoveLine, self)._log_message(
                record, move, template, vals)
