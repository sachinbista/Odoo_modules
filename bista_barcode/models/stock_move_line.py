# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    demand_qty = fields.Float(related="move_id.product_uom_qty", store=True)
    demand_uom = fields.Many2one("uom.uom", related="move_id.product_uom", store=True)

    def trigger_check_availability(self, picking_ids):
        if not picking_ids:
            return

        picking = self.env['stock.picking'].browse(picking_ids)
        for x in picking:
            x.action_assign()
            x.action_assign()

    def replace_move_lot(self, lot_id, location_id):
        if not lot_id:
            return
        lot = self.env['stock.lot'].browse(lot_id)

        lot_location = self._get_lot_location(lot)

        if lot_location.id == location_id:
            return False

        # Check if Source location and lot location is different return message
        src_location = self.env['stock.location'].browse(location_id)
        message = _('Serial/Lot (%s) is not located in %s, but is located in location(s): %s.\n\n'
                    'Source location for this move will be changed to %s',
                    lot.name, src_location.display_name, lot_location.display_name, lot_location.display_name)
        return {'message': message, "location_id": {'id': lot_location.id,
                                                    'name': lot_location.name,
                                                    'barcode': lot_location.barcode,
                                                    'parent_path': lot_location.parent_path,
                                                    'display_name': lot_location.display_name,
                                                    'usage': lot_location.usage}}

    def _get_lot_location(self, lot_id):
        domain = [('location_id.usage', 'in', ['transit', 'internal']),
                  ('quantity', '!=', 0),
                  ('lot_id', '=', lot_id.id)]
        quant = self.env['stock.quant'].search(domain, limit=1)
        lot_location = quant.location_id
        self.location_id = lot_location.id

        if not lot_location:
            raise UserError("This serial number is not available in any of the accessible stock location.")
        return lot_location

    def get_uom_qty(self, product_uom_id, uom_id, qty):
        uom_env = self.env['uom.uom']
        product_uom = uom_env.browse(product_uom_id)
        uom = uom_env.browse(uom_id)
        return product_uom._compute_quantity(qty, uom, rounding_method='HALF-UP')

    def _get_fields_stock_barcode(self):
        ret = super(StockMoveLine, self)._get_fields_stock_barcode()
        ret.append('demand_qty')
        ret.append("demand_uom")
        return ret
