# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class MoveBoxAndPallet(models.Model):
    _name = "fds.move_box_and_pallet"
    _inherit = ['barcodes.barcode_events_mixin']
    _description = "Move - Boxs & Pallets"
    _order = 'transfer_sequence, id'

    picking_id = fields.Many2one('stock.picking', string="Picking", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    transfer_sequence = fields.Integer(
        string='Transfer Sequence',
        related='product_id.transfer_sequence',
        store=True)
    tracking = fields.Selection(related='product_id.tracking', readonly=True)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    picking_code = fields.Selection(related='picking_id.picking_type_id.code', readonly=True)
    picking_location_id = fields.Many2one(related='picking_id.location_id')
    picking_location_dest_id = fields.Many2one(related='picking_id.location_dest_id')
    picking_type_use_create_lots = fields.Boolean(related='picking_id.picking_type_id.use_create_lots', readonly=True)
    picking_type_use_existing_lots = fields.Boolean(related='picking_id.picking_type_id.use_existing_lots', readonly=True)
    picking_type_entire_packs = fields.Boolean(related='picking_id.picking_type_id.show_entire_packs', readonly=True)
    company_id = fields.Many2one('res.company', string="Company", related='picking_id.company_id')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id', store=True)
    move_ids = fields.One2many(
        'stock.move', 'move_box_pallet_id', string='Operations')
    product_uom_qty = fields.Float(string='Demand', compute='_compute_all')
    product_qty = fields.Float(string='Demand', compute='_compute_all')
    forecast_availability = fields.Float(
        string='Reserved',
        digits='Product Unit of Measure',
        compute='_compute_all')
    forecast_expected_date = fields.Datetime('Forecasted Expected date', compute='_compute_all', compute_sudo=True)
    reserved_availability = fields.Float(
        'Quantity Reserved',
        digits='Product Unit of Measure',
        readonly=True, help='Quantity that has already been reserved for this move', compute='_compute_all')
    quantity_done = fields.Float(string='Done', compute='_compute_all')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure', compute='_compute_all'
    )
    box_and_pallet = fields.Integer(
        'Box/Pallet',
        help='Number of Box/Pallet', compute='_compute_all')
    loose = fields.Integer(
        'Loose',
        help='Loose quantity', compute='_compute_all')
    product_type = fields.Selection(related='product_id.detailed_type', readonly=True)
    is_locked = fields.Boolean(compute='_compute_is_locked', readonly=True)
    state = fields.Selection([
        ('draft', 'New'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')], string='Status',
        copy=False, default='draft', index=True, readonly=True,
        help="* New: When the stock move is created and not yet confirmed.\n"
             "* Waiting Another Move: This state can be seen when a move is waiting for another one, for example in a chained flow.\n"
             "* Waiting Availability: This state is reached when the procurement resolution is not straight forward. It may need the scheduler to run, a component to be manufactured...\n"
             "* Available: When products are reserved, it is set to \'Available\'.\n"
             "* Done: When the shipment is processed, the state is \'Done\'.",
        compute='_compute_all')
    line_display_name = fields.Char(compute='_compute_all', recursive=True, index=True)
    line_product_uom_qty = fields.Float(
        'Reserved', default=0.0, digits='Product Unit of Measure',
        compute='_compute_all')
    qty_done = fields.Float(
        'Done', digits='Product Unit of Measure',
        compute='_compute_all',
        inverse='_set_qty_done')
    line_location_id = fields.Many2one(
        'stock.location', 'From', compute='_compute_all')
    line_location_dest_id = fields.Many2one(
        'stock.location', 'To', compute='_compute_all')
    line_box_and_pallet = fields.Integer(
        'Box/Pallet',
        help='Number of Box/Pallet', compute='_compute_all')
    line_loose = fields.Integer(
        'Loose',
        help='Loose quantity',
        compute='_compute_all')
    package_id = fields.Many2one(
        'stock.quant.package', 'Source Package', ondelete='restrict',
        check_company=True,
        domain="[('location_id', '=', line_location_id)]",
        compute='_compute_package',
        inverse='_inverse_package')
    result_package_id = fields.Many2one(
        'stock.quant.package', 'Destination Package',
        ondelete='restrict', required=False, check_company=True,
        domain="['|', '|', ('location_id', '=', False), ('location_id', '=', line_location_dest_id), ('id', '=', package_id)]",
        help="If set, the operations are packed into this package",
        compute='_compute_package',
        inverse='_inverse_package')
    owner_id = fields.Many2one(
        'res.partner', 'From Owner',
        check_company=True,
        help="When validating the transfer, the products will be taken from this owner.",
        compute='_compute_owner_id')
    description_picking = fields.Text(string="Description picking", compute='_compute_all')
    date = fields.Datetime(
        'Date Scheduled',
        compute='_compute_date',
        help="Scheduled date until move is done, then date of actual move processing")
    date_deadline = fields.Datetime(
        "Deadline",
        compute='_compute_date',
        help="Date Promise to the customer on the top level document (SO/PO)")
    is_completed = fields.Boolean(compute='_compute_all', help="Check if the quantity done matches the demand")
    # Barcode
    product_barcode = fields.Char(related='product_id.barcode')
    dummy_id = fields.Char(compute='_compute_dummy_id', inverse='_inverse_dummy_id')
    product_stock_quant_ids = fields.One2many('stock.quant', compute='_compute_product_stock_quant_ids')

    @property
    def move_lines(self):
        return self.move_ids.mapped('move_line_ids')

    def _compute_date(self):
        for obj in self:
            moves = obj.move_ids
            obj.date = moves and moves[0].date or False
            obj.date_deadline = moves and moves[0].date_deadline or False

    def _compute_owner_id(self):
        for obj in self:
            move_lines = obj.move_lines
            obj.owner_id = move_lines and move_lines[0].owner_id or False

    def _compute_package(self):
        for obj in self:
            move_lines = obj.move_lines
            obj.package_id = move_lines and move_lines[0].package_id or False
            obj.result_package_id = move_lines and move_lines[0].result_package_id or False

    def _inverse_package(self):
        for obj in self:
            obj.move_lines.write({
                'package_id': obj.package_id and obj.package_id.id or False,
                'result_package_id': obj.result_package_id and obj.result_package_id.id or False,
            })

    def _compute_product_stock_quant_ids(self):
        for obj in self:
            obj.product_stock_quant_ids = obj.product_id.stock_quant_ids.filtered(lambda q: q.company_id in self.env.companies and q.location_id.usage == 'internal')

    def _compute_dummy_id(self):
        self.dummy_id = ''

    def _inverse_dummy_id(self):
        pass

    def _compute_all(self):
        BoxPallet = self.env['fds.box_and_pallet']
        product_template_ids = self.mapped('product_tmpl_id').ids
        product_tmp_box_pallet = BoxPallet.get_box_pallet_by_product_template_list(product_template_ids)
        for item in self:
            moves = item.move_ids
            item.product_uom_qty = sum(moves.mapped('product_uom_qty'))
            item.product_qty = sum(moves.mapped('product_qty'))
            item.forecast_availability = sum(moves.mapped('forecast_availability'))
            item.forecast_expected_date = moves and moves[0].forecast_expected_date or False
            item.reserved_availability = sum(moves.mapped('reserved_availability'))
            item.quantity_done = sum(moves.mapped('quantity_done'))
            item.product_uom_id = moves and moves[0].product_uom or False
            item.description_picking = moves and moves[0].description_picking or ''
            item.is_completed = all(moves.mapped('move_line_ids.is_completed'))
            # TODO: to clarify which state is prefer if there are more than 1 move
            item.state = moves and moves[0].state or False

            # move lines
            item.line_display_name = moves and moves[0].display_name or ''
            item.line_product_uom_qty = sum(moves.mapped('move_line_ids.reserved_uom_qty'))
            item.qty_done = sum(moves.mapped('move_line_ids.qty_done'))
            item.line_location_id = moves and moves[0].location_id or False
            item.line_location_dest_id = moves and moves[0].location_dest_id or False

            # Box and pallets
            box_and_pallet, loose = 0, 0
            line_box_and_pallet, line_loose = 0, 0
            if product_box_pallet_qty := product_tmp_box_pallet.get(item.product_tmpl_id.id, False):
                box_and_pallet, loose = BoxPallet.compute_box_pallet_loose(
                    product_box_pallet_qty, sum(moves.mapped('product_uom_qty')))

                line_box_pallet_mapping = moves and moves[0].state != 'done' and 'move_line_ids.reserved_uom_qty' or 'move_line_ids.qty_done'
                line_box_and_pallet, line_loose = BoxPallet.compute_box_pallet_loose(
                    product_box_pallet_qty, sum(moves.mapped(line_box_pallet_mapping)))

            item.box_and_pallet = box_and_pallet
            item.loose = loose
            item.line_box_and_pallet = line_box_and_pallet
            item.line_loose = line_loose

    @api.depends('picking_id.is_locked')
    def _compute_is_locked(self):
        for move in self:
            if move.picking_id:
                move.is_locked = move.picking_id.is_locked
            else:
                move.is_locked = False

    def _set_qty_done(self):
        for obj in self:
            done_qty = obj.qty_done
            if not obj.move_ids:
                # create stock.move.line
                vals = obj._prepare_stock_move_line_vals()
                move = obj.move_ids.move_line_ids.create(vals)
                move.move_id.move_box_pallet_id = obj
            else:
                for line in obj.move_ids.move_line_ids:
                    line.qty_done = min(done_qty, line.reserved_uom_qty)
                    done_qty -= min(done_qty, line.reserved_uom_qty)

                if done_qty > 0 and obj.move_ids.move_line_ids:
                    # Put all left qty to last move line.
                    obj.move_ids.move_line_ids[-1].qty_done += done_qty

    def _prepare_stock_move_line_vals(self):
        # {
        #     'company_id': 1,
        #     'reserved_uom_qty': 0,
        #     'move_id': False,
        #     'picking_id': 68,
        #     'location_id': 4,
        #     'location_dest_id': 8,
        #     'product_id': 19,
        #     'qty_done': 2,
        #     'lot_name': False,
        #     'lot_id': False
        # }
        vals = {
            'company_id': self.picking_id.company_id.id,
            'reserved_uom_qty': 0,
            'move_id': False,
            'picking_id': self.picking_id.id,
            'product_id': self.product_id.id,
            'qty_done': self.qty_done,
            'product_uom_id': self.product_uom_id.id or self.product_id.uom_id.id,
            'location_id': self.picking_id.location_id.id,
            'location_dest_id': self.picking_id.location_dest_id.id,
        }
        return vals

    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'line_location_id',
            'line_location_dest_id',
            'qty_done',
            'line_display_name',
            'line_product_uom_qty',
            'product_uom_id',
            'product_barcode',
            'owner_id',
            # 'lot_id',
            # 'lot_name',
            'package_id',
            'result_package_id',
            'dummy_id',
            'line_box_and_pallet',
            'line_loose',
            'move_ids'
        ]

    def update(self):
        """When stock.move is delete. If there is no move. Delete object"""
        to_delete = self.browse()
        for obj in self:
            if not obj.move_ids:
                to_delete |= obj

        if to_delete:
            to_delete.unlink()
