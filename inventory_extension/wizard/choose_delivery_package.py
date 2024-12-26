# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class ChooseDeliveryPackage(models.TransientModel):
    _inherit = 'choose.delivery.package'

    choose_line_ids = fields.One2many('choose.delivery.package.line',
                                      'choose_id',
                                      string="Choose Moves to Pack")
    selected_all = fields.Boolean(string="Selected All")

    @api.onchange('delivery_package_type_id', 'shipping_weight', 'selected_all')
    def _onchange_package_type_weight(self):
        return super(ChooseDeliveryPackage,
                     self)._onchange_package_type_weight()

    def action_select_all(self):
        if self.choose_line_ids:
            filtered_choose_line_ids = self.choose_line_ids.filtered(lambda l: l.move_qty > 0)
            filtered_choose_line_ids.selected = True
            if len(filtered_choose_line_ids) == len(self.choose_line_ids):
                self.selected_all = True
        return {
            'name': _('Package Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'choose.delivery.package',
            'res_id': self.id,
            'target': 'new',
            'context': self._context,
        }

    def action_deselect_all(self):
        if self.choose_line_ids:
            self.choose_line_ids.selected = False
            self.selected_all = False
        return {
            'name': _('Package Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'choose.delivery.package',
            'res_id': self.id,
            'target': 'new',
            'context': self._context,
        }

    @api.depends('delivery_package_type_id', 'choose_line_ids',
                 'choose_line_ids.selected', 'choose_line_ids.move_qty',
                 'selected_all')
    def _compute_shipping_weight(self):
        for rec in self:
            choose_line_ids = rec.choose_line_ids.filtered(
                lambda l: l.selected
                          and l.move_qty > 0)
            if not choose_line_ids:
                move_line_ids = rec.picking_id.move_line_ids.filtered(
                    lambda m:
                    float_compare(
                        m.quantity,
                        0.0,
                        precision_rounding=m.product_uom_id.rounding) > 0
                    and not m.result_package_id
                )
                # Add package weights to shipping weight, package base weight is defined in package.type
                total_weight = rec.delivery_package_type_id.base_weight or 0.0
                for ml in move_line_ids:
                    qty = ml.product_uom_id._compute_quantity(
                        ml.quantity,
                        ml.product_id.uom_id)
                    total_weight += qty * ml.product_id.weight
            else:
                total_weight = rec.delivery_package_type_id.base_weight or 0.0
                for ml in choose_line_ids:
                    qty = (
                        ml.stock_move_line_id.product_uom_id
                        ._compute_quantity(ml.move_qty,
                                           ml.stock_move_line_id.product_id.uom_id))
                    total_weight += (qty *
                                     ml.stock_move_line_id.product_id.weight)

            rec.shipping_weight = total_weight

    @api.model
    def default_get(self, default_fields):
        res = super(ChooseDeliveryPackage, self).default_get(
            default_fields)
        if res.get('picking_id'):
            picking_id = self.env['stock.picking'].browse([res['picking_id']])
            if picking_id:
                move_line_dict = []
                move_line_ids = picking_id.move_line_ids.filtered(
                    lambda m: float_compare(
                        m.quantity, 0.0,
                        precision_rounding=m.product_uom_id.rounding) > 0 and
                              not m.result_package_id
                )
                if move_line_ids:
                    for move in move_line_ids:
                        move_line_dict.append((0, 0, {
                            'stock_move_line_id': move.id,
                            'actual_move_qty': move.quantity,
                            'move_qty': move.quantity
                        }))
                if move_line_dict:
                    res.update({
                        'choose_line_ids': move_line_dict
                    })
        return res

    def action_put_in_pack(self):
        if self.delivery_package_type_id.max_weight and self.shipping_weight > self.delivery_package_type_id.max_weight:
            warning_mess = ('The weight of your package is higher than the '
                            'maximum weight authorized for this package type. Please choose another package type.')
            raise ValidationError(_(warning_mess))

        if self.choose_line_ids and not self.choose_line_ids.filtered(lambda x: x.selected and x.move_qty > 0):
            raise ValidationError(_('Please select minimum of one line to proceed.'))
        else:
            if self.choose_line_ids:
                move_line_ids = self.choose_line_ids.filtered(
                    lambda l: l.selected and l.move_qty > 0)
                if move_line_ids:
                    for move in move_line_ids:
                        qty = move.move_qty
                        if qty < move.actual_move_qty:
                            move.stock_move_line_id.copy({
                                'quantity': move.actual_move_qty - qty})
                            move.stock_move_line_id.quantity = qty
                    move_line_ids = move_line_ids.mapped('stock_move_line_id')
                else:
                    move_line_ids = self.picking_id._package_move_lines(
                        batch_pack=self.env.context.get("batch_pack"))
            else:
                move_line_ids = self.picking_id._package_move_lines(
                    batch_pack=self.env.context.get("batch_pack"))

            delivery_package = self.picking_id._put_in_pack(move_line_ids)
            # write shipping weight and package type on 'stock_quant_package' if needed
            if self.delivery_package_type_id:
                delivery_package.package_type_id = self.delivery_package_type_id
            if self.shipping_weight:
                delivery_package.shipping_weight = self.shipping_weight
            return self.picking_id._post_put_in_pack_hook(delivery_package)


class ChooseDeliveryPackageLine(models.TransientModel):
    _name = 'choose.delivery.package.line'

    selected = fields.Boolean(string="Select to Put in Pack")
    stock_move_line_id = fields.Many2one('stock.move.line',
                                         string="Product Lines", readonly=True)
    actual_move_qty = fields.Float(string="Picked Quantity")
    move_qty = fields.Float(string="Pack Quantity")
    choose_id = fields.Many2one('choose.delivery.package', string="Choose Pack")

    @api.onchange('move_qty')
    def _onchange_move_qty(self):
        if self.move_qty and (self.move_qty > self.actual_move_qty or self.move_qty < 0):
            raise ValidationError(_('Packed Quantity should be positive and less than Actual Quantity'))
        if self.move_qty == 0:
            self.selected = False
            self._origin.choose_id.write({'selected_all': False})
