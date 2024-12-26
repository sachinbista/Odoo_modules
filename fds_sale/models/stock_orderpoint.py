from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    qty_committed = fields.Float(
        'Committed', readonly=True, compute='_compute_qty_committed', digits='Product Unit of Measure')

    @api.depends('product_id', 'location_id', 'product_id.stock_move_ids', 'product_id.stock_move_ids.state',
                 'product_id.stock_move_ids.date', 'product_id.stock_move_ids.product_uom_qty',
                 'product_id.stock_move_ids.picking_type_id')
    def _compute_qty_committed(self):
        StockMove = self.env['stock.move.line'].with_context(active_test=False)
        if self.env.company.name == 'Fence & Deck Supply':
            type_committed_order = self.env.ref('fds_sale.stock_picking_type_committed_orders')
        else:
            type_committed_order = self.env.ref('fds_sale.stock_picking_type_committed_orders_fds_new')
        product_ids = self.mapped('product_id').ids
        domain = [
            ('product_id', 'in', product_ids),
            ('picking_id.picking_type_id', '=', type_committed_order.id),
            ('state', 'in', ('assigned',)),
            ('location_id', '=', type_committed_order.default_location_src_id.id)
        ]
        moves = dict((item['product_id'][0], item['reserved_qty']) for item in StockMove._read_group(domain, ['product_id', 'reserved_qty'], ['product_id'], orderby='id'))
        for orderpoint in self:
            orderpoint.qty_committed = moves.get(orderpoint.product_id.id, 0.0)
