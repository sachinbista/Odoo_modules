# -*- coding: utf-8 -*-

from odoo import models, api


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ctx = dict(self._context)
        if ctx.get('location_id') and ctx.get('product_id'):
            quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', ctx['product_id']),
                ('location_id', '=', ctx['location_id'])
            ]).mapped('lot_id')
            args = [('id', 'in', quants.ids)]
        return super(StockLot, self).name_search(
            name=name, args=args, operator=operator, limit=limit)

    @api.model
    def search_read(
            self, domain=None, fields=None, offset=0, limit=None, order=None):
        ctx = dict(self._context)
        if ctx.get('location_id') and ctx.get('product_id'):
            quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', ctx['product_id']),
                ('location_id', '=', ctx['location_id'])
            ]).mapped('lot_id')
            args = [('id', 'in', quants.ids)]
        return super(StockLot, self).search_read(
            domain, fields, offset, limit, order)
