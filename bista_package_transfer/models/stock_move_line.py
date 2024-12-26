from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.onchange('product_id', 'location_id')
    def onchange_product_set_package(self):
        if self.product_id and self.location_id and not self.package_id:
            quant_id = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', self.location_id.id),
                ('package_id', '!=', False)])
            if quant_id and len(quant_id) == 1:
                self.package_id = quant_id.package_id.id

    @api.onchange('qty_done')
    def onchange_done_qty(self):
        if self.product_id and self.qty_done > 1 and self.picking_type_id.code == 'internal' and self.location_dest_id.id == 24812:
            quant_domain = [('product_id', '=', self.product_id.id), ('location_id', '=', self.location_id.id)]
            if self.package_id:
                quant_domain += [('package_id', '=', self.package_id.id)]
            else:
                quant_domain += [('package_id', '=', False)]
            available_quant = self.env['stock.quant'].search(quant_domain)
            available_qty = available_quant and available_quant.quantity or 0
            if not self.package_id and (not available_quant or available_qty < self.qty_done):
                raise UserError(_(F"Product {self.product_id.name} is not fully available without package.\n"
                                  "Please select package to transfer."))
            if available_qty < self.qty_done and self.package_id:
                raise UserError(_(
                    F"You are trying to transfer more than available quantity for "
                    F"product {self.product_id.name} with package {self.package_id.name}.\n"
                    F"Available quantity: {available_qty}"))
            if available_qty > self.qty_done and self.result_package_id:
                self.result_package_id = False

    def _action_done(self):
        for ml in self:
            if ml.product_id and ml.qty_done > 0 and ml.picking_type_id.code == 'internal' and ml.location_dest_id.id == 24812:
                quant_domain = [('product_id', '=', ml.product_id.id), ('location_id', '=', ml.location_id.id)]
                if ml.package_id:
                    quant_domain += [('package_id', '=', ml.package_id.id)]
                else:
                    quant_domain += [('package_id', '=', False)]
                available_quant = self.env['stock.quant'].search(quant_domain)
                available_qty = available_quant.quantity or 0
                if not ml.package_id and (not available_quant or available_qty < ml.qty_done):
                    raise UserError(_(
                        F"Product {ml.product_id.name} is not fully available without package.\n"
                        F"Please select package to transfer."))
                if available_qty < ml.qty_done and ml.package_id:
                    raise UserError(_(
                        F"You are trying to transfer more than available quantity for "
                        F"product {ml.product_id.name} with package {ml.package_id.name}.\n"
                        F"Available quantity: {available_qty}"))
                if available_qty > ml.qty_done and ml.result_package_id:
                    ml.result_package_id = False
            super(StockMoveLine, ml)._action_done()

    # @api.onchange('result_package_id', 'product_id', 'product_uom_id', 'qty_done')
    # def _onchange_putaway_location(self):
    #     default_dest_location = self._get_default_dest_location()
    #     package_count = self.env['stock.quant.package'].search([('location_id', '=', self.location_dest_id.id),])
    #     print("package_count===========================>",package_count.name)
    #     if self.location_dest_id.single_package_allowed and len(package_count) > 0:
    #         raise exceptions.UserError(
    #             _("Already one package exists in this location. You can't put two packages at this location."))
    #     if not self.id and self.user_has_groups('stock.group_stock_multi_locations') and self.product_id and self.qty_done \
    #             and self.location_dest_id == default_dest_location:
    #         qty_done = self.product_uom_id._compute_quantity(self.qty_done, self.product_id.uom_id)
    #         self.location_dest_id = default_dest_location.with_context(exclude_sml_ids=self.ids)._get_putaway_strategy(
    #             self.product_id, quantity=qty_done, package=self.result_package_id,
    #             packaging=self.move_id.product_packaging_id)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_quick_transfer_assign(self, line):
        """ Reserve stock moves by creating their stock move lines. A stock move is
        considered reserved once the sum of `reserved_qty` for all its move lines is
        equal to its `product_qty`. If it is less, the stock move is considered
        partially available.
        """
        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.reserved_availability for move in self}
        roundings = {move: move.product_id.uom_id.rounding for move in self}
        move_line_vals_list = []
        # Once the quantities are assigned, we want to find a better destination location thanks
        # to the putaway rules. This redirection will be applied on moves of `moves_to_redirect`.
        moves_to_redirect = OrderedSet()
        moves_to_assign = self

        for move in moves_to_assign:
            rounding = roundings[move]
            if float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
                assigned_moves_ids.add(move.id)
            elif not move.move_orig_ids:
                if move.procure_method == 'make_to_order':
                    continue
                # If we don't need any quantity, consider the move assigned.
                need = line.qty_transfer
                if float_is_zero(need, precision_rounding=rounding):
                    assigned_moves_ids.add(move.id)
                    continue
                # Reserve new quants and create move lines accordingly.
                forced_package_id = line.package_id or None
                available_quantity = move._get_available_quantity(line.source_location_id, package_id=forced_package_id)
                if available_quantity <= 0:
                    continue
                taken_quantity = move._update_reserved_quantity(need, available_quantity, line.source_location_id, package_id=forced_package_id, strict=False)
                if float_is_zero(taken_quantity, precision_rounding=rounding):
                    continue
                moves_to_redirect.add(move.id)
                if float_compare(need, taken_quantity, precision_rounding=rounding) == 0:
                    assigned_moves_ids.add(move.id)
                else:
                    partially_available_moves_ids.add(move.id)
                
            if move.product_id.tracking == 'serial':
                move.next_serial_count = move.product_uom_qty
        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})