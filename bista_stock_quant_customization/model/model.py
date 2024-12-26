# File: models/purchase_order_line.py

from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        if self.purchase_id:
            self.action_put_in_pack()
        res = super(StockPicking, self).button_validate()
        return res

#
# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#     purchase_qty = fields.Char(string="Purchase Qty")
#     purchase_uom = fields.Char(string="Purchase UOM")
#
#     def _get_new_picking_values(self):
#         vals = super(StockMove, self)._get_new_picking_values()
#         if self.purchase_line_id:
#             vals.update({
#                 'purchase_qty': self.purchase_line_id.product_qty,
#                 'purchase_uom': self.purchase_line_id.product_uom,
#             })
#         return vals


#
# class StockQuant(models.Model):
#     _inherit = 'stock.quant'
#
#     purchase_qty = fields.Char(string="Purchase Qty")
#     purchase_uom = fields.Char(string="Purchase UOM")
#

# class StockMoveLine(models.Model):
#     _inherit = 'stock.move.line'
#
#     def _create_and_assign_production_lot(self):
#         lot = super(StockMoveLine, self)._create_and_assign_production_lot()
#         if lot and self.move_id:
#             lot.write({
#                 'purchase_qty': self.move_id.purchase_qty,
#                 'purchase_uom': self.move_id.purchase_uom,
#             })
#         return lot


# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     # def _create_move_from_pos_order_lines(self, lines):
#     #     moves = super(StockPicking, self)._create_move_from_pos_order_lines(lines)
#     #     for move in moves:
#     #         if move.purchase_line_id:
#     #             move.write({
#     #                 'purchase_qty': move.purchase_line_id.product_qty,
#     #                 'purchase_uom': move.purchase_line_id.product_uom,
#     #             })
#     #     return moves
#
#     def button_validate(self):
#         self.action_put_in_pack()
#         res = super(StockPicking, self).button_validate()
#         return res
        # for move in self.move_ids:
        #     if move.state == 'done':
        #         # Update only the quants created or updated by this move
        #         quants = self.env['stock.quant'].search([
        #             ('product_id', '=', move.product_id.id),
        #             ('location_id', '=', move.location_dest_id.id),
        #             ('lot_id', 'in', move.move_line_ids.mapped('lot_id').ids),
        #             ('in_date', '>=', move.date),
        #             # This assumes the quant was created/updated on or after the move date
        #         ])
        #
        #
        #         for quant in quants:
        #             quant.write({
        #                 'purchase_qty': move.purchase_line_id.product_qty,
        #                 'purchase_uom': move.purchase_line_id.product_uom.name,
        #             })


        # return res
