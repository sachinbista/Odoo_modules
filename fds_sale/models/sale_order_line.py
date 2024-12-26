from odoo import models, api, fields, SUPERUSER_ID
from odoo.tools import float_compare, OrderedSet
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        lines.filtered(lambda line: line.state == 'committed')._action_launch_committed_transfer()
        return lines

    def write(self, values):
        """Update Committed Orders."""
        lines = self.env['sale.order.line']
        if 'product_uom_qty' in values:
            lines = self.filtered(lambda r: r.state == 'committed' and not r.is_expense)

        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        res = super(SaleOrderLine, self).write(values)
        if lines:
            lines._action_launch_committed_transfer(previous_product_uom_qty)
        return res

    def _action_launch_committed_transfer(self, previous_product_uom_qty=False):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        group_id = None
        movel_vals_list = []
        kits_by_product = self.env['mrp.bom']._bom_find(self.mapped('product_id'), bom_type='phantom')
        for line in self:
            line = line.with_company(line.company_id)
            # Allow create DO when SO is in `committed`
            if line.state not in ['committed'] or line.product_id.type not in ('consu', 'product') or\
                    not line.order_id.warehouse_id.commit_type_id:
                continue

            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            product_qty = line.product_uom_qty - qty
            bom_kit = kits_by_product.get(line.product_id)
            if bom_kit:
                boms, bom_sub_lines = bom_kit.explode(line.product_id, product_qty)
                for bom_line, bom_line_data in bom_sub_lines:
                    movel_vals_list.append(
                        line._prepare_stock_move_vals(
                            group_id, bom_line.product_id, bom_line.product_uom_id,
                            bom_line_data['qty'], bom_line_id=bom_line.id)
                        )
            else:
                movel_vals_list.append(line._prepare_stock_move_vals(
                    group_id, line.product_id, line.product_uom, product_qty))

        if group_id:
            self._create_committed_moves(movel_vals_list)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
        return True

    def _prepare_stock_move_vals(self, group_id, product, product_uom, product_qty, bom_line_id=False):
        procurement_vals = self._prepare_procurement_values(group_id)
        picking_type_committed = procurement_vals['warehouse_id'].commit_type_id
        picking_description = self.product_id._get_description(picking_type_committed)
        if procurement_vals.get('product_description_variants'):
            picking_description += procurement_vals['product_description_variants']
        vals = {
            'name': self.name,
            'company_id': procurement_vals['company_id'].id,
            'product_id': product.id,
            'product_uom': product_uom.id,
            'product_uom_qty': product_qty,
            'partner_id': procurement_vals['partner_id'],
            'location_id': picking_type_committed.default_location_src_id.id,
            'location_dest_id': picking_type_committed.default_location_dest_id.id,
            'procure_method': 'make_to_stock',
            'origin': self.order_id.name,
            'picking_type_id': picking_type_committed.id,
            'group_id': group_id.id,
            'route_ids': [],
            'warehouse_id': procurement_vals['warehouse_id'].id,
            'date': fields.Datetime.now(),
            'date_deadline': procurement_vals['date_deadline'],
            'propagate_cancel': False,
            'description_picking': picking_description,
            'priority': '0',
            'sale_line_id': self.id,
            'sequence': procurement_vals['sequence'],
            'bom_line_id': bom_line_id
        }
        return vals

    def _create_committed_moves(self, movel_vals_list):
        StockMove = self.env['stock.move']
        company_id = self[0].order_id.company_id
        moves = StockMove.with_user(SUPERUSER_ID).sudo().with_company(company_id).create(movel_vals_list)
        moves._action_confirm()
        return moves

    def _get_sale_order_line_multiline_description_variants(self):
        result = super(SaleOrderLine, self)._get_sale_order_line_multiline_description_variants()
        kit_abbreviated_description = self._get_kit_abbreviated_description()
        if kit_abbreviated_description:
            result += f"\n\nEach Kit includes:{kit_abbreviated_description}"
        return result

    def _get_kit_abbreviated_description(self):
        kit_abbreviated_description = ''
        kits_by_product = self.env['mrp.bom']._bom_find(self.product_id, bom_type='phantom')
        bom_kit = kits_by_product.get(self.product_id)
        if bom_kit:
            _, bom_sub_lines = bom_kit.explode(self.product_id, 1)
            for bom_line, _ in bom_sub_lines:
                if abbreviated_description := bom_line.abbreviated_description:
                    kit_abbreviated_description += f"\n- {abbreviated_description} - {bom_line.product_qty}"
        return kit_abbreviated_description

    def delete_move(self):
        """Delete move in committed transfer."""
        # At this state, there are only one picking
        picking = self.order_id.picking_ids
        if picking and len(picking) == 1:
            lines = self.filtered(lambda l: l.state == 'committed')
            products = lines.mapped("product_id")
            move_to_delete = picking.move_lines.filtered(lambda m: m.product_id in products)
            if move_to_delete:
                move_to_delete.unlink()

    def unlink(self):
        self.delete_move()
        return super(SaleOrderLine, self).unlink()
