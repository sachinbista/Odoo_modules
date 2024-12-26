import logging
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'
    _order = 'transfer_sequence, sequence, id'

    box_and_pallet = fields.Integer(
        'Box/Pallet',
        compute='_compute_box_and_pallet',
        # store=True,
        help='Number of Box/Pallet')
    loose = fields.Integer(
        'Loose',
        compute='_compute_box_and_pallet',
        # store=True,
        help='Loose quantity')
    move_box_pallet_id = fields.Many2one(
        'fds.move_box_and_pallet',
        string='Move - Boxs & Pallet')
    transfer_sequence = fields.Integer(
        string='Transfer Sequence',
        related='product_id.transfer_sequence',
        store=True)

    @api.depends('product_uom_qty', 'product_id')
    def _compute_box_and_pallet(self):
        BoxPallet = self.env['fds.box_and_pallet']
        product_template_ids = self.mapped('product_id.product_tmpl_id').ids
        product_tmp_box_pallet = BoxPallet.get_box_pallet_by_product_template_list(product_template_ids)

        for move in self:
            box_and_pallet, loose = 0, 0
            product_tmp_id = move.product_id.product_tmpl_id.id
            product_uom_qty = move.product_uom_qty

            if product_box_pallet_qty := product_tmp_box_pallet.get(product_tmp_id, False):
                box_and_pallet, loose = BoxPallet.compute_box_pallet_loose(product_box_pallet_qty, product_uom_qty)
            move.box_and_pallet = box_and_pallet
            move.loose = loose

    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        returns: dictionary {product_id+name+description+uom: {product, name, description, qty_done, product_uom}, ...}
        """
        aggregated_move_lines = {}

        def get_aggregated_properties(move):
            uom = move.product_uom
            name = move.product_id.display_name
            description = move.description_picking
            if description == name or description == move.product_id.name:
                description = False
            product = move.product_id
            line_key = f'{product.id}_{product.display_name}_{description or ""}_{uom.id}'
            return (line_key, name, description, uom)

        for move in self:
            line_key, name, description, uom = get_aggregated_properties(move)

            quantity_done = move.product_uom._compute_quantity(move.quantity_done, uom)
            quantity_order = move.product_uom._compute_quantity(move.product_uom_qty, uom)
            if line_key not in aggregated_move_lines:
                aggregated_move_lines[line_key] = {
                    'name': name,
                    'description': description,
                    'qty_done': quantity_done,
                    'qty_ordered': quantity_order or quantity_done,
                    'product_uom': uom.name,
                    'product_uom_rec': uom,
                    'product': move.product_id
                }
            else:
                aggregated_move_lines[line_key]['qty_ordered'] += quantity_order
                aggregated_move_lines[line_key]['qty_done'] += quantity_done

        return aggregated_move_lines

    def _assign_picking_post_process(self, new=False):
        super(StockMove, self)._assign_picking_post_process(new=new)
        self.mapped('picking_id')._update_move_box_pallets()

    def unlink(self):
        move_box_pallet_ids = self.mapped('move_box_pallet_id')
        res = super(StockMove, self).unlink()
        if move_box_pallet_ids:
            move_box_pallet_ids.update()
        return res
