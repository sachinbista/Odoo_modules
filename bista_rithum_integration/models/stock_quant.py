# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model_create_multi
    def create(self, vals_list):
        quants = super().create(vals_list)
        quants.mapped('product_id').write({'is_rithum_qty_changed': True})
        return quants

    def write(self, vals):
        res = super().write(vals)
        if 'quantity' in vals or 'reserved_quantity' in vals:
            self.mapped('product_id').write({'is_rithum_qty_changed': True})
        return res