from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleLineReport(models.Model):
    _name = "sale.line.report"
    _description = "Sale Line Report"
    _rec_name = 'order_date'
    _order = 'priority asc, scheduled_date asc'

    name = fields.Char('Order Reference', readonly=True)
    sequence = fields.Integer(string="Sequence")
    order_id = fields.Many2one('sale.order', 'Order Reference',  readonly=True)
    order_date = fields.Datetime('Order Date', readonly=True)
    order_status = fields.Selection(related="order_id.state", string="Order Status", readonly=True,store=True)

    sub_line = fields.One2many(comodel_name='sale.sub.line.report',
                               inverse_name='line_report_id',
                               string="Sub Lines",
                               copy=True, auto_join=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    move_id = fields.Many2one('stock.move', 'Move', readonly=True)
    # move_status = fields.Selection(related="move_id.state", readonly=True)
    scheduled_date = fields.Datetime(related='move_id.date')
    picking_id = fields.Many2one('stock.picking', 'Picking', readonly=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', readonly=True)
    # picking_status = fields.Selection(related="move_id.move_orig_ids.picking_id.state", readonly=True)
    picking_scheduled_date = fields.Datetime(related='picking_id.scheduled_date')
    picking_status = fields.Selection(related="picking_id.state", string="Picking Status", readonly=True,store=True)
    priority = fields.Integer(string="Priority", track_visibility='always')
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True,
                                 readonly=True, precompute=True, index=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='order_id.warehouse_id',
                                   readonly=True,store=True)
    delivery_status = fields.Selection(related="order_id.delivery_status", string='Delivery Status',store=True)
    def write(self, vals):
        result = super(SaleLineReport, self).write(vals)
        priority = vals.get('priority')
        if priority:
            picking_ids = self.filtered(lambda r: r.order_id and r.order_id.state in ('sent', 'hold', 'sale')).mapped(
                'order_id.picking_ids')
            picking_ids.write({'picking_priority': priority})

        return result

    # def name_get(self):
    #     result = []
    #     for line_report in self:
    #         name = line_report.name
    #         result.append((line_report.id, name))
    #     return result

    def button_reserve(self):
        for rec in self.filtered(lambda s: s.move_id.state in ('waiting', 'confirmed')):
            rec.move_id.move_orig_ids.move_orig_ids._action_assign()
            if rec.move_id.product_id.qty_available < rec.move_id.product_uom_qty:
                raise ValidationError('Not enough on-hand quantity for product {}'.format(rec.move_id.product_id.name))

    def button_unreserve(self):
        for rec in self.filtered(lambda s: s.picking_status in ('assigned')):
            rec.move_id.move_orig_ids.move_orig_ids._do_unreserve()


class SaleSubLineReport(models.Model):
    _name = "sale.sub.line.report"
    _description = "Sale Sub Line Report"

    line_report_id = fields.Many2one('sale.line.report')

    so_line_id = fields.Many2one('sale.order.line', string='Related SO Line', readonly=True)
    product_uom_qty = fields.Float('Order Qty', readonly=True,related='so_line_id.product_uom_qty')
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    # qoh_available = fields.Float(string="On Hand", compute='_compute_sale_qoh')
    # back_order_qty = fields.Float(string="Back Order Qty", compute="_compute_sale_boq")
    picking_id = fields.Many2one('stock.picking', 'Picking', readonly=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', readonly=True)
    # priority = fields.Integer(string="Priority")
    picking_status = fields.Selection(related="picking_id.state", readonly=True)
    display_qty_widget = fields.Boolean(compute='_compute_sale_qoh')
    display_warehouse_qty_widget = fields.Boolean(related="display_qty_widget")
    qty_delivered = fields.Float(string="Quantity Delivered")

    @api.depends('product_id')
    def _compute_sale_qoh(self):
        for rec in self:
            # rec.qoh_available = rec.product_id.qty_available
            rec.display_qty_widget = True if rec.product_id.qty_available else False
            rec.display_warehouse_qty_widget = True if rec.product_id.qty_available else False

    # @api.depends('so_line_id.qty_delivered')
    # def _compute_sale_boq(self):
    #     stock_move_obj = self.env['stock.move']
    #     for rec in self:
    #         if rec.so_line_id.qty_delivered > 1:
    #             stock_moves = stock_move_obj.search(
    #                 [('sale_line_id', '=', rec.so_line_id.id), ('state', '=', 'assigned')])
    #             back_qty = 0
    #             for stock_move in stock_moves:
    #                 if stock_move.picking_id.backorder_id:
    #                     back_qty += stock_move.product_uom_qty
    #             rec.back_order_qty = back_qty
    #         else:
    #             rec.back_order_qty = 0

    # def name_get(self):
    #     result = []
    #     for line_report in self:
    #         name = (
    #             f"{line_report.product_id.name} => Ordered Qty - {line_report.product_uom_qty}, "
    #             f"On Hand Qty - {line_report.qoh_available}, Back Order Qty - {line_report.back_order_qty}"
    #         )
    #         result.append((line_report.id, name))
    #     return result


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self.create_sale_line_report()
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        # self.cancel_sale_line_report()
        return res

    def create_sale_line_report(self):
        line_report_obj = self.env['sale.line.report']
        stock_move_obj = self.env['stock.move']
        data = []

        for order in self:
            picking_type_id = picking_id = priority = move_id = 0
            sub_lines = []

            for line in order.order_line:
                order_picking = order.picking_ids.filtered(lambda picking: picking.picking_type_id.code == 'outgoing')

                if order_picking:
                    picking_type_id = order_picking.picking_type_id[0].id
                    picking_id = order_picking[0].id
                    stock_move_data = self.env['stock.move'].search([('picking_id', '=', order_picking[0].id)], limit=1)
                    move_id = stock_move_data if stock_move_data else False

                if line.product_id.type != 'service':
                    stock_move = stock_move_obj.search([('sale_line_id', '=', line.id), ('state', '!=', 'cancel')],
                                                       limit=1)
                    priority = self.get_priority(stock_move)
                    vals = (0, 0, {
                        'so_line_id': line.id,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'picking_type_id': stock_move.picking_type_id[0].id if stock_move else False,
                        # 'priority': priority,
                        'picking_id': stock_move.picking_id[0].id if stock_move else False,
                    })
                    sub_lines.append(vals)

            vals = {
                'name': order.name,
                'order_id': order.id,
                'order_date': order.date_order,
                'sub_line': sub_lines,
                'partner_id': order.partner_id.id,
                'picking_type_id': picking_type_id,
                'priority': priority,
                'picking_id': picking_id,
                'move_id': move_id.id if move_id else False,
            }
            data.append(vals)
        line_report_obj.sudo().create(data)

    def cancel_sale_line_report(self):
        line_report_obj = self.env['sale.line.report']
        for order in self:
            data = []
            for line in order.order_line:
                report_line = line_report_obj.search([('so_line_id', '=', line.id)])
                if report_line:
                    report_line.picking_status = 'Cancel'

    def get_priority(self, move):
        shduler_obj = self.env['truck.schedular']
        cutoff_time = 14.00
        now = datetime.now().time()
        current_time = round(float(now.hour + now.minute / 60.0), 2)

        date_only = datetime.utcnow().strftime('%Y-%m-%d')

        # First, check with date_only
        cutoff = shduler_obj.search([('holiday', '=', date_only)], order="priority ASC", limit=1)

        if not cutoff:
            # If no record found, check with other criteria
            location_id = move.location_dest_id[0].id if move.location_dest_id else False
            cutoff = shduler_obj.search(
                ['|', '|', '|', ('customers_id', '=', move.partner_id.id),
                 ('location_id', '=', location_id),
                 ('carrier_id', '=', move.picking_id.carrier_id.id), ('holiday', '=', date_only)],
                limit=1)
        if cutoff:
            cutoff_time = round(float(cutoff.cutoff_time), 2)

        if str(cutoff.holiday) != date_only:
            if current_time > cutoff_time:
                for each in move:
                    if each.picking_id.state not in ['done', 'cancel']:
                        each.picking_id.scheduled_date = each.picking_id.scheduled_date + timedelta(days=1)
        else:
            for each in move:
                if each.picking_id.state not in ['done', 'cancel']:
                    each.picking_id.scheduled_date = each.picking_id.scheduled_date + timedelta(days=1)

        if move.route_ids:
            return move.route_ids[0].picking_priority
        else:
            return 1

        # if str(cutoff.holiday) != date_only:
        #     if current_time < cutoff_time:
        #         if rec.total_product_uom_qty > 6:
        #             return 1
        #         elif rec.total_product_uom_qty == 1:
        #             return 4
        #         elif rec.total_product_uom_qty > 1 and rec.total_product_uom_qty < 7:
        #             return 5
        #     else:
        #         picking.scheduled_date = picking.scheduled_date + timedelta(days=1)
        #         if rec.total_product_uom_qty > 6:
        #             return 1
        #         elif rec.total_product_uom_qty == 1:
        #             return 4
        #         elif rec.total_product_uom_qty > 1 and rec.total_product_uom_qty < 7:
        #             return 5
        # else:
        #     picking.scheduled_date = picking.scheduled_date + timedelta(days=1)
        #     if rec.total_product_uom_qty > 6:
        #         return 1
        #     elif rec.total_product_uom_qty == 1:
        #         return 4
        #     elif rec.total_product_uom_qty > 1 and rec.total_product_uom_qty < 7:
        #         return 5
    @api.depends('delivery_status')
    def _order_delivery_status_update(self):
        for rec in self:
            if rec.delivery_status == 'full':
                order_line_report = self.env['sale.line.report'].serach([('order_id','=',rec.id)])
                if order_line_report:
                    order_line_report.sub_line.unlink()
                    order_line_report.unlink()


class StockRoute(models.Model):
    _inherit = 'stock.route'

    picking_priority = fields.Integer(string="Picking Priority")
