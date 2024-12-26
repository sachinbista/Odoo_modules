# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_move_default_values(self, return_line, new_picking):
        '''Method inherited to update the stock move lines fufillment details'''
        vals = super(ReturnPicking, self)._prepare_move_default_values(
            return_line=return_line, new_picking=new_picking)
        move_id = return_line.move_id
        if move_id:
            vals.update({
                'shopify_item_line_id': move_id.shopify_item_line_id or '',
                'shopify_assigned_location_id': move_id.shopify_assigned_location_id or '',
                'shopify_fulfillment_order_id': move_id.shopify_fulfillment_order_id or '',
                'shopify_fulfillment_line_id': move_id.shopify_fulfillment_line_id or ''
            })
        return vals
