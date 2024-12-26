from odoo import models, fields, api, Command, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
import logging
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby

_logger = logging.getLogger(__name__)


class StockRoute(models.Model):
    _inherit = "stock.route"

    route_domain = fields.Char("Sale Order Conditions")
    picking_type_selectable = fields.Boolean("Picking Type Selectable")
    picking_type_ids = fields.Many2many('stock.picking.type', string="Operation Types")
    single_picking = fields.Boolean("Single Picking")


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _get_rule(self, product_id, location_id, values):
        """ Find a pull rule for the location_id, fallback on the parent
        locations if it could not be found.

        Custom comment
        Extended this function for multi route concept on the basis of route configuration
        """
        order_line = values.get('sale_line_id')
        order_line = self.env['sale.order.line'].browse(order_line)
        # if not order_line:
        #     if self.env.context.get('sale_order_ref'):
        #         order_line = self.env.context.get('sale_order_ref').order_line[0]

        order_pickings = all(picking.state == 'cancel' for picking in order_line.order_id.picking_ids)
        if order_pickings or not order_line.order_id.picking_ids:
            if 'sale_line_id' in values or self.env.context.get('sale_stock_transfer'):
                Rule = self.env['stock.rule']
                res = self.env['stock.rule']
                # order_line = self.env['sale.order.line'].browse(values['sale_line_id'])
                warehouse_id = values.get('warehouse_id', False)
                route_ids = values.get('route_ids', False)
                packaging_id = values.get('product_packaging_id', False)
                domain = []
                custom_routes = ''

                if self.env.context.get('sale_stock_transfer') and 'stock_transfer_line_id' in values:
                    # warehouse_id = warehouse_id.resupply_warehouse_id if warehouse_id.resupply_warehouse_id else warehouse_id
                    if warehouse_id:
                        domain = expression.AND([['|', ('warehouse_id', '=', warehouse_id.id), ('warehouse_id', '=', False)], domain])
                    if route_ids:
                        res = Rule.search(expression.AND([[('route_id', 'in', route_ids.ids)], domain]),order='route_sequence, sequence', limit=1)
                    if not res and packaging_id:
                        custom_routes = packaging_id.sudo().route_ids
                        if custom_routes:
                            res = Rule.search(expression.AND([[('route_id', 'in', custom_routes.ids)], domain]),order='route_sequence, sequence', limit=1)
                    if not res:
                        custom_routes = product_id.route_ids | product_id.categ_id.sudo().total_route_ids.filtered(lambda a:a.warehouse_ids in warehouse_id)
                        if custom_routes:
                            res = Rule.search(expression.AND([[('route_id', 'in', custom_routes.ids)], domain]),order='route_sequence, sequence', limit=1)
                    if not res and warehouse_id:
                        custom_routes = warehouse_id.sudo().route_ids
                        if custom_routes:
                            res = Rule.search(expression.AND([[('route_id', 'in', custom_routes.ids)], domain]),order='route_sequence, sequence', limit=1)

                    order_id = self.env.context.get('sale_order_ref')
                    stock_transfer_line = values.get('stock_transfer_line_id')
                    product_volume = stock_transfer_line.product_id.volume
                    product_inventory_volume = self.env['ir.config_parameter'].sudo().get_param('sale_stock_extend.product_inventory_volume')
                    if product_inventory_volume and product_volume > 0 and product_volume > int(product_inventory_volume) and order_id.total_product_uom_qty < 7:
                        values['route_ids'] = self.env['stock.route'].sudo().search([('single_picking', '=', True)])
                    else:

                        for custom_route in custom_routes:
                            route_domain = []
                            if custom_route.route_domain:
                                route_domain = safe_eval(custom_route.route_domain)
                                route_domain.append(('id', '=', order_id.id))
                                check_sale_order = self.env['sale.order'].search(route_domain)

                                if check_sale_order:
                                    if 'route_ids' not in values:
                                        values['route_ids'] = custom_route
                                    else:
                                        values['route_ids'] += custom_route

                else:
                    if warehouse_id:
                        domain = expression.AND([['|', ('warehouse_id', '=', warehouse_id.id), ('warehouse_id', '=', False)], domain])
                    if route_ids:
                        res = Rule.search(expression.AND([[('route_id', 'in', route_ids.ids)], domain]),order='route_sequence, sequence', limit=1)
                    if not res and packaging_id:
                        custom_routes = packaging_id.route_ids
                        if custom_routes:
                            res = Rule.search(expression.AND([[('route_id', 'in', custom_routes.ids)], domain]),order='route_sequence, sequence', limit=1)
                    if not res:
                        custom_routes = product_id.route_ids | product_id.categ_id.total_route_ids.filtered(lambda a:a.warehouse_ids in warehouse_id)
                        if custom_routes:
                            res = Rule.search(expression.AND([[('route_id', 'in', custom_routes.ids)], domain]),order='route_sequence, sequence', limit=1)
                    if not res and warehouse_id:
                        custom_routes = warehouse_id.route_ids
                        if custom_routes:
                            res = Rule.search(expression.AND([[('route_id', 'in', custom_routes.ids)], domain]),order='route_sequence, sequence', limit=1)
                    if not warehouse_id.resupply_warehouse_id:
                        product_volume = order_line.product_id.volume
                        product_inventory_volume = self.env['ir.config_parameter'].sudo().get_param('sale_stock_extend.product_inventory_volume')
                        if product_inventory_volume and product_volume > 0 and product_volume > int(product_inventory_volume) and order_line.order_id.total_product_uom_qty < 7:
                            values['route_ids'] = self.env['stock.route'].sudo().search([('single_picking','=',True)])
                            order_line.write({'is_single_ship': True})
                        else:
                            order_line.write({'is_single_ship': False})
                            for custom_route in custom_routes:
                                route_domain = []
                                if custom_route.route_domain:
                                    route_domain = safe_eval(custom_route.route_domain)
                                    route_domain.append(('id','=',order_line.order_id.id))
                                    check_sale_order = self.env['sale.order'].search(route_domain)

                                    if check_sale_order:
                                        values['route_ids'] += custom_route
                                        order_line.write({'route_id': custom_route.id})
                                else:
                                    order_line.write({'route_id': custom_route.id})

            # _logger.info('routes to create picking: %s', values)
        return super(ProcurementGroup, self)._get_rule(product_id, location_id, values)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        existing_picking = []
        for rec in self:
            existing_picking = self.env['stock.picking'].search([('origin', '=', rec.origin)])
        if not existing_picking:
            if self.warehouse_id.multi_route:
                Picking = self.env['stock.picking']
                grouped_moves = groupby(self, key=lambda m: m._key_assign_picking())
                for group, moves in grouped_moves:
                    moves = self.env['stock.move'].concat(*moves)
                    new_picking = False
                    # Could pass the arguments contained in group but they are the same
                    # for each move that why moves[0] is acceptable
                    picking = moves[0]._search_picking_for_assignation()
                    if picking:
                        # If a picking is found, we'll append `move` to its move list and thus its
                        # `partner_id` and `ref` field will refer to multiple records. In this
                        # case, we chose to wipe them.
                        vals = {}
                        if any(picking.partner_id.id != m.partner_id.id for m in moves):
                            vals['partner_id'] = False
                        if any(picking.origin != m.origin for m in moves):
                            vals['origin'] = False
                        if vals:
                            picking.write(vals)
                    else:
                        # Don't create picking for negative moves since they will be
                        # reverse and assign to another picking
                        moves = moves.filtered(lambda m: float_compare(m.product_uom_qty, 0.0, precision_rounding=m.product_uom.rounding) >= 0)
                        if not moves:
                            continue
                        new_picking = True
                        # storage_move = moves.filtered(lambda a: a.product_id.volume > int(self.env['ir.config_parameter'].sudo().get_param('sale_stock_extend.product_inventory_volume')))
                        storage_move = moves.filtered(lambda a: a.sale_line_id.is_single_ship == True or a.product_id.volume > 200)
                        if storage_move:
                            for mv in storage_move:
                                new_picking = True
                                picking = Picking.create(mv._get_new_picking_values())
                                mv.write({'picking_id': picking.id})
                                mv._assign_picking_post_process(new=new_picking)

                        moves = moves.filtered(lambda a: a.sale_line_id.is_single_ship == False)
                        if moves:
                            picking = Picking.create(moves._get_new_picking_values())

                            moves.write({'picking_id': picking.id})
                            moves._assign_picking_post_process(new=new_picking)
            else:
                keys = super(StockMove, self)._assign_picking()
        else:
            keys = super(StockMove, self)._assign_picking()
        return True

    def _action_confirm(self, merge=True, merge_into=False):
        ''' Split Move For Delivery two or three steps according '''
        for record in self:
            if not record.sale_line_id:
                origin_move_id = self.env['stock.move'].search([('move_orig_ids', '=', record.id), ('sale_line_id', '!=', False)])
                if origin_move_id:
                    for origin_move in origin_move_id:
                        record.update({'sale_line_id': origin_move.sale_line_id.id})
        return super(StockMove, self)._action_confirm(merge=merge, merge_into=merge_into)

class Stock(models.Model):
    _inherit = 'stock.warehouse'

    multi_route = fields.Boolean("Multi Route Warehosue")
