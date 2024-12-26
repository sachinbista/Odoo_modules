import json
import requests
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleLineChangeOrder(models.TransientModel):
    _name = 'sale.line.change.order'
    _description = 'Sale Line Change Order'

    order_id = fields.Many2one('sale.order', string='Sale Order',default=lambda self: self.env.context.get('active_id', None),)
    line_ids = fields.One2many('sale.line.change.order.line', 'change_order_id', string='Change Lines')

    @api.model
    def default_get(self, fields):
        rec = super(SaleLineChangeOrder, self).default_get(fields)
        if 'order_id' in rec:
            order = self.env['sale.order'].browse(rec['order_id'])
            if not order:
                return rec

            line_model = self.env['sale.line.change.order.line']
            rec['line_ids'] = [(0, 0, line_model.values_from_so_line(l)) for l in order.order_line.filtered(lambda x: x.product_id.type != 'service')]
        return rec

    def apply(self):
        self.ensure_one()
        self.line_ids.apply()
        return True


class SaleLineChangeOrderLine(models.TransientModel):
    _name = 'sale.line.change.order.line'
    _description = 'Sale Line Change Order Line'

    change_order_id = fields.Many2one('sale.line.change.order')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Line')
    line_ordered_qty = fields.Float(string='Ordered Qty')
    line_delivered_qty = fields.Float(string='Delivered Qty')
    line_reserved_qty = fields.Float(string='Reserved Qty')
    line_date_planned = fields.Datetime(string='Planned Date')
    line_warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    line_route_id = fields.Many2one('stock.route', string='Route')

    def values_from_so_line(self, so_line):
        move_ids = so_line.move_ids
        reserved_qty = sum(move_ids.mapped('quantity'))
        return {
            'sale_line_id': so_line.id,
            'line_ordered_qty': so_line.product_uom_qty,
            'line_delivered_qty': so_line.qty_delivered,
            'line_reserved_qty': reserved_qty,
            'line_date_planned': so_line.scheduled_date,
            'line_warehouse_id': so_line.warehouse_id.id,
            'line_route_id': so_line.route_id.id,
        }

    def _apply(self):
        self._apply_clean_dropship()
        self._apply_clean_existing_moves()
        self._apply_new_values()
        self._apply_procurement()
        self.update_shopify_order_id()
        self.create_new_fullfillments()

    def _apply_clean_dropship(self):
        po_line_model = self.env['purchase.order.line'].sudo()
        po_lines = po_line_model.search([('sale_line_id', 'in', self.mapped('sale_line_id.id'))])

        if po_lines and po_lines.filtered(lambda l: l.order_id.state != 'cancel'):
            names = ', '.join(po_lines.filtered(lambda l: l.order_id.state != 'cancel').mapped('order_id.name'))
            raise ValidationError('One or more lines has existing non-cancelled Purchase Orders associated: ' + names)

    def _apply_clean_existing_moves(self):
        moves = self.mapped('sale_line_id.move_ids').filtered(lambda m: m.state != 'done')
        moves._action_cancel()
        moves.unlink()

    def _apply_new_values(self):
        shopify_location_map_obj = self.env['shopify.location.mapping']
        for line in self:
            mapping_location_id = False
            if line.line_warehouse_id and line.sale_line_id.order_id.shopify_config_id:
                mapping_location_id = shopify_location_map_obj.search(
                    [('warehouse_id', '=', line.line_warehouse_id.id),
                     ('shopify_config_id', '=',
                      line.sale_line_id.order_id.shopify_config_id.id)
                     ], limit=1)
                if not mapping_location_id:
                    raise ValidationError(
                        _("""%s Warehouse is not mapped with shopify locations. So cannot linked with sales order line for shopify sales order.""" % (
                            line.line_warehouse_id.display_name)))
            line.sale_line_id.write({
                'scheduled_date': line.line_date_planned,
                'warehouse_id': line.line_warehouse_id.id,
                'route_id': line.line_route_id.id,
                'assigned_location_id': mapping_location_id and mapping_location_id.shopify_location_id or '',
                'shopify_location_id': mapping_location_id and mapping_location_id.shopify_location_id or ''
            })

    def update_shopify_order_id(self):
        for line in self:
            if line.sale_line_id.order_id.picking_ids.filtered(
                    lambda p: not p.shopify_config_id and not p.shopify_order_id):
                [picking.write({
                    'shopify_config_id': line.sale_line_id.order_id.shopify_config_id.id,
                    'shopify_order_id': line.sale_line_id.order_id.shopify_order_id,
                }) for picking in
                    line.sale_line_id.order_id.picking_ids]

    def create_new_fullfillments(self):
        '''Method to only update location in shopify order when location is
        changed into pickings'''

        move_lines = self.env['stock.move']
        for line in self:
            if line.line_warehouse_id and \
                    line.sale_line_id.move_ids.filtered(
                    lambda p: p.state not in ('cancel', 'done')):
                move_lines |= line.sale_line_id.move_ids.filtered(
                    lambda p: p.state not in ('cancel', 'done'))

        move_request_dict = []
        for each in move_lines.filtered(
                lambda m: m.picking_id and
                          m.picking_id.picking_type_id.code in (
                                  'outgoing')):

            shopify_config = each.picking_id.sale_id.shopify_config_id
            location_mapping_id = self.env[
                'shopify.location.mapping'].search([
                ('odoo_location_id', '=', each.location_id.id),
                ('shopify_config_id', '=', shopify_config.id)],
                limit=1)
            if location_mapping_id:
                headers = {
                    'X-Shopify-Access-Token':
                        each.picking_id.sale_id.shopify_config_id.password,
                    'Content-Type': 'application/json'}
                sale_line_id = (
                    each.picking_id.sale_id.order_line.filtered(
                        lambda
                            l: l.product_id.id == each.product_id.id
                               and l.shopify_fulfillment_line_id)
                )
                url = shopify_config.shop_url
                fulfillment_order_id = sale_line_id.shopify_fulfillment_order_id
                api_order_url = (
                                    "/admin/api/2023-10/fulfillment_orders/%s/move.json") % (
                                    fulfillment_order_id)
                url = url + api_order_url
                if sale_line_id:
                    body = {"fulfillment_order": {
                        "new_location_id": location_mapping_id.shopify_location_id,
                        "fulfillment_order_line_items": [{
                            'id': sale_line_id.shopify_fulfillment_line_id,
                            'quantity': int(
                                each.product_uom_qty)}]}}
                    if body:
                        move_request_dict.append({
                            'url': url, 'data': body,
                            'headers': headers, 'move_id': each})
        for move_req in move_request_dict:
            try:
                response = requests.request('POST', move_req.get('url'),
                                            headers=move_req.get('headers'),
                                            data=json.dumps(
                                                move_req.get('data')))
                fulfillment_dict = response.json()
                if fulfillment_dict.get('moved_fulfillment_order'):
                    shopify_fulfillment_order_id = fulfillment_dict.get(
                        'moved_fulfillment_order').get('id')
                    line_items = fulfillment_dict.get(
                        'moved_fulfillment_order').get('line_items')
                    shopify_fulfillment_line_id = line_items[0].get('id')
                    if shopify_fulfillment_order_id \
                            and shopify_fulfillment_line_id:
                        ctx = dict(self._context) or {}
                        ctx.update({'move_update_from_fulfillment': True})
                        move_req.get('move_id').with_context(ctx).write({
                            'shopify_fulfillment_order_id':
                                shopify_fulfillment_order_id,
                            'shopify_fulfillment_line_id': shopify_fulfillment_line_id})
                        if move_req.get('move_id').sale_line_id:
                            move_req.get('move_id').sale_line_id.with_context(ctx).write({
                                'shopify_fulfillment_order_id':
                                    shopify_fulfillment_order_id,
                                'shopify_fulfillment_line_id': shopify_fulfillment_line_id})
                if fulfillment_dict.get('errors'):
                    raise ValidationError(_(fulfillment_dict['errors']))
            except Exception as e:
                error_message = 'Error in updating location on shopify : {}'.format(
                    e)
                raise ValidationError(_(error_message))

    def _apply_procurement(self):
        self.mapped('sale_line_id')._action_launch_stock_rule()

    def apply(self):
        changed_lines = self.filtered(lambda l: (
                l.sale_line_id.warehouse_id != l.line_warehouse_id
                or l.sale_line_id.route_id != l.line_route_id))
        changed_lines._apply()
