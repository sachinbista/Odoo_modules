from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime

class GoflowSplitOrderWiz(models.TransientModel):
    _name = "goflow.split.order.wiz"
    _description = "goflow.split.order.wiz"
    
    split_order_wiz_line = fields.One2many('goflow.split.order.wiz.line', 'split_order_wiz_id')

    def default_get(self, fields):
        res = super(GoflowSplitOrderWiz, self).default_get(fields)
        stock_picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        wiz_line = []
        for line in stock_picking.move_line_ids_without_package :
            wiz_line.append((0,0,{
                'product_id': line.product_id.id,
                'total_qty': line.reserved_uom_qty,
                'uom_id': line.product_uom_id.id
            }))
        if wiz_line:
            res['split_order_wiz_line'] = wiz_line
        return res

    def split_order(self):
        stock_picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        if stock_picking:
            # print("stock_picking:::::::::::::::::::::",stock_picking)
            for move_line in stock_picking.move_line_ids_without_package:
                for wiz_line in self.split_order_wiz_line:
                    if move_line.product_id.id == wiz_line.product_id.id:
                        move_line.qty_done = wiz_line.done_qty

            # calling split order API
            stock_picking.goflow_split_order()

class GoflowSplitOrderWizLine(models.TransientModel):
    _name = "goflow.split.order.wiz.line"
    _description = "goflow.split.order.wiz.line"

    split_order_wiz_id = fields.Many2one('goflow.split.order.wiz')

    product_id = fields.Many2one('product.product', "Product")
    total_qty = fields.Float('Total Qty')
    done_qty = fields.Float('Done Qty')
    uom_id = fields.Many2one('uom.uom', "Unit of Measure")