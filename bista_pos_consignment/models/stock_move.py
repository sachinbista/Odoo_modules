# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################
from collections import defaultdict
from datetime import timedelta
from operator import itemgetter

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round



class StockMove(models.Model):
    _inherit = "stock.move"

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
                                  owner_id=None, strict=True):
        self.ensure_one()
        if self.consignment_stock_move:
            if not lot_id:
                lot_id = self.env['stock.lot']
            if not package_id:
                package_id = self.env['stock.quant.package']
            if not owner_id:
                owner_id = self.env['res.partner']

            # do full packaging reservation when it's needed
            if self.product_packaging_id and self.product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full":
                available_quantity = self.product_packaging_id._check_qty(available_quantity, self.product_id.uom_id,
                                                                          "DOWN")

            taken_quantity = min(available_quantity, need)
            if not strict and self.product_id.uom_id != self.product_uom:
                taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(taken_quantity, self.product_uom,
                                                                                   rounding_method='DOWN')
                taken_quantity = self.product_uom._compute_quantity(taken_quantity_move_uom, self.product_id.uom_id,
                                                                    rounding_method='HALF-UP')

            quants = []
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')

            if self.product_id.tracking == 'serial':
                if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                    taken_quantity = 0

            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                        if self.consignment_stock_move:
                            quants = self.env['stock.quant'].with_context({'owner_value':True})._update_reserved_quantity(
                                self.product_id, location_id, taken_quantity, lot_id=lot_id,
                                package_id=package_id, owner_id=owner_id, strict=strict
                            )
                        else:
                            quants = self.env['stock.quant']._update_reserved_quantity(
                                self.product_id, location_id, taken_quantity, lot_id=lot_id,
                                package_id=package_id, owner_id=owner_id, strict=strict
                            )
            except UserError:
                taken_quantity = 0

            # Find a candidate move line to update or create a new one.
            serial_move_line_vals = []
            for reserved_quant, quantity in quants:
                to_update = next(
                    (line for line in self.move_line_ids if line._reservation_is_updatable(quantity, reserved_quant)),
                    False)
                if to_update:
                    uom_quantity = self.product_id.uom_id._compute_quantity(quantity, to_update.product_uom_id,
                                                                            rounding_method='HALF-UP')
                    uom_quantity = float_round(uom_quantity, precision_digits=rounding)
                    uom_quantity_back_to_product_uom = to_update.product_uom_id._compute_quantity(uom_quantity,
                                                                                                  self.product_id.uom_id,
                                                                                                  rounding_method='HALF-UP')
                if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                    to_update.with_context(bypass_reservation_update=True).reserved_uom_qty += uom_quantity
                else:
                    if self.product_id.tracking == 'serial':
                        # Move lines with serial tracked product_id cannot be to-update candidates. Delay the creation to speed up candidates search + create.
                        serial_move_line_vals.extend(
                            [self._prepare_move_line_vals(quantity=1, reserved_quant=reserved_quant) for i in
                             range(int(quantity))])
                    else:
                        self.env['stock.move.line'].create(
                            self._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant))
            self.env['stock.move.line'].create(serial_move_line_vals)
            return taken_quantity
        else:
            return super()._update_reserved_quantity(need, available_quantity, location_id, lot_id, package_id,owner_id, strict)




    def _get_available_quantity(self, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, allow_negative=False):
        if self.consignment_stock_move and not location_id.should_bypass_reservation():
           return  self.env['stock.quant'].with_context({'owner_value':True})._get_available_quantity(self.product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict, allow_negative=allow_negative)

        else:
            return super(StockMove, self)._get_available_quantity(location_id, lot_id, package_id, owner_id, strict, allow_negative)







