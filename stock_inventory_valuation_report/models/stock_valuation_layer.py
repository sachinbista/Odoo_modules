# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""
    _inherit = 'stock.valuation.layer'

    warehouse_id = fields.Many2one('stock.warehouse',
                            string='Warehouse')

    @api.model
    def create(self, vals):
        if vals.get('stock_move_id', False) and\
        vals.get('quantity'):
            sm_id = self.env['stock.move'].browse(vals.get('stock_move_id'))
            if sm_id and sm_id.location_dest_id and\
                sm_id.location_dest_id.usage == 'internal':
                vals.update({
                    'warehouse_id': sm_id.location_dest_id.warehouse_id.id
                    })
            if sm_id and sm_id.location_id and\
                sm_id.location_id.usage == 'internal':
                vals.update({
                    'warehouse_id': sm_id.location_id.warehouse_id.id
                    })
        res = super(StockValuationLayer, self).create(vals)
        return res