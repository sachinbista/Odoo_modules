import logging
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    _order = "transfer_sequence, result_package_id desc, location_id asc, location_dest_id asc, picking_id asc, id"

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
    transfer_sequence = fields.Integer(
        string='Transfer Sequence',
        related='product_id.transfer_sequence',
        store=True)

    @api.depends('reserved_uom_qty', 'product_id')
    def _compute_box_and_pallet(self):
        BoxPallet = self.env['fds.box_and_pallet']
        product_template_ids = self.mapped('product_id.product_tmpl_id').ids
        product_tmp_box_pallet = BoxPallet.get_box_pallet_by_product_template_list(product_template_ids)

        for move in self:
            box_and_pallet, loose = 0, 0
            product_tmp_id = move.product_id.product_tmpl_id.id
            product_uom_qty = move.reserved_uom_qty

            if product_box_pallet_qty := product_tmp_box_pallet.get(product_tmp_id, False):
                box_and_pallet, loose = BoxPallet.compute_box_pallet_loose(product_box_pallet_qty, product_uom_qty)
            move.box_and_pallet = box_and_pallet
            move.loose = loose

    # def _get_fields_stock_barcode(self):
    #     """Show box_and_pallet and loose value on Barcode Screen."""
    #     fields = super(StockMoveLine, self)._get_fields_stock_barcode()
    #     return fields + ['box_and_pallet', 'loose']
