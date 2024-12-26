import logging
from odoo import api, fields, models, _
from odoo.tools import groupby
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    move_box_pallet_ids = fields.One2many(
        'fds.move_box_and_pallet', 'picking_id', string='Box & Pallet Operations')
    move_line_box_pallet_ids = fields.One2many(
        'fds.move_box_and_pallet', 'picking_id', string='Box & Pallet Operations',
        compute='_compute_move_line_box_pallet_ids', readonly=False)
    show_box_pallet = fields.Boolean(
        compute='_compute_show_box_pallet',
        # search='_search_show_box_pallet'
    )

    def _compute_show_box_pallet(self):
        """Show box/pallet for Commit, PICK and Delivery Order type."""
        for picking in self:
            warehouse = picking.picking_type_id.warehouse_id
            picking.show_box_pallet = picking.picking_type_id in (
                warehouse.pick_type_id,
                warehouse.pack_type_id,
                warehouse.out_type_id,
                warehouse.commit_type_id
            )

    def _compute_move_line_box_pallet_ids(self):
        for picking in self:
            picking.move_line_box_pallet_ids = picking.move_box_pallet_ids.filtered(
                lambda m: m.line_product_uom_qty > 0 or m.qty_done > 0
            )

    def _create_backorder(self):
        backorders = super(StockPicking, self)._create_backorder()
        for picking in self:
            picking._update_move_box_pallets()
        for picking in backorders:
            picking._update_move_box_pallets()
        return backorders

    def _update_move_box_pallets(self):
        moves_by_product = {
            product: [m.id for m in moves]
            for product, moves in groupby(self.move_ids, lambda m: m.product_id)
        }
        MoveBoxPallet = self.env['fds.move_box_and_pallet']
        mbp_to_delete = MoveBoxPallet.browse()
        for mbp in self.move_box_pallet_ids:
            if move_ids := moves_by_product.get(mbp.product_id, []):
                mbp.write({'move_ids': [(6, 0, move_ids)]})
                del moves_by_product[mbp.product_id]
            else:
                mbp_to_delete |= mbp

        if mbp_to_delete:
            mbp_to_delete.unlink()

        move_box_vals = []
        for product, move_ids in moves_by_product.items():
            move_box_vals.append(self._prepare_move_box_pallet_values(product, move_ids))

        if move_box_vals:
            MoveBoxPallet.create(move_box_vals)

    def _prepare_move_box_pallet_values(self, product, move_ids):
        return {
            'picking_id': self.id,
            'product_id': product.id,
            'move_ids': [(6, 0, move_ids)]
        }

    def _get_fields_stock_barcode(self):
        res = super(StockPicking, self)._get_fields_stock_barcode()
        res.append('move_line_box_pallet_ids')
        return res

    def _get_stock_barcode_data(self):
        """Add move_line_box_pallet_ids data."""
        datas = super(StockPicking, self)._get_stock_barcode_data()
        move_box_and_pallet = self.move_line_box_pallet_ids
        datas['picking_type_code'] = self.picking_type_code
        if self.picking_type_code == 'outgoing':
            datas['records'].update({
                'fds.move_box_and_pallet': move_box_and_pallet.read(move_box_and_pallet._get_fields_stock_barcode(), load=False),
            })
            datas.update({
                'line_view_id': self.env.ref('fds_stock.move_box_and_pallet_product_selector').id
            })
        return datas
    
    def _pre_put_in_pack_hook(self, move_line_ids):
        res = super(StockPicking, self)._pre_put_in_pack_hook(move_line_ids)
        if not res:
            return self._set_package_value()
        return res
    
    def _set_package_value(self):
        if 'package_height' not in self._context:
            view_id = self.env.ref('fds_stock.view_set_package_value').id
            wiz = self.env['set.package.value'].create({
                'picking_id': self.id,
            })
            return {
                'name': _('Set Package Value'),
                'view_mode': 'form',
                'res_model': 'set.package.value',
                'view_id': view_id,
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': wiz.id,
                'target': 'new'
            }
        return {}

    def _put_in_pack(self, move_line_ids, create_package_level=True):
        package = super(StockPicking, self)._put_in_pack(move_line_ids, create_package_level)
        if package and 'package_height' in self._context:
            package.write({
                'package_height': self._context.get('package_height', 0),
                'package_weight': self._context.get('package_weight', 0),
                'package_depth': self._context.get('package_depth', 0),
                'package_type_id': self._context.get('package_type_id', False),
            })
        return package
    
    def _action_done(self):
        """Inherit to create scrap oder for package product."""
        res = super(StockPicking, self)._action_done()
        # {
        #   'lang': 'en_US',
        #   'tz': 'Asia/Bangkok',
        #   'uid': 2,
        #   'allowed_company_ids': [1],
        #   'active_model': 'sale.order',
        #   'active_id': 41,
        #   'active_ids': [41],
        #   'default_partner_id': 14,
        #   'default_picking_type_id': 19,
        #   'default_origin': 'S00041',
        #   'default_group_id': 28,
        #   'button_validate_picking_ids': [62],
        #   'cancel_backorder': False
        # }
        # Prevent some default value when create stock.scrap -> stock.move
        default_context_keys = ('lang', 'tz', 'uid')
        ctx = {
            key: self._context.get(key)
            for key in default_context_keys
        }
        self.move_line_ids.mapped('result_package_id').with_context(ctx).create_scrap_oders()
        return res
