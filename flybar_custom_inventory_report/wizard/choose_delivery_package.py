# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError
from odoo.exceptions import Warning


class ChooseDeliveryPackage(models.TransientModel):
    _inherit = 'choose.delivery.package'
    _description = 'Delivery Package Selection Wizard'

    product_length = fields.Float("length")
    product_width = fields.Float("width")
    product_height = fields.Float("height")

    @api.depends('delivery_package_type_id')
    def _compute_shipping_weight(self):
        for rec in self:
            move_line_ids = rec.picking_id.move_line_ids.filtered(lambda m:
                            float_compare(m.qty_done, 0.0,precision_rounding=m.product_uom_id.rounding) > 0
                            and not m.result_package_id
                            )

            total_weight = rec.delivery_package_type_id.base_weight or 0.0
            move_line_ids_max_dimension = max(move_line_ids, key=lambda m: m.product_id.volume, default=None)
            for ml in move_line_ids:
                total_weight += ml.product_id.weight

            rec.shipping_weight = total_weight
            rec.product_length = move_line_ids_max_dimension.product_id.product_length if move_line_ids_max_dimension else 0.0
            rec.product_width = move_line_ids_max_dimension.product_id.product_width if move_line_ids_max_dimension else 0.0
            rec.product_height = move_line_ids_max_dimension.product_id.product_height if move_line_ids_max_dimension else 0.0

    def action_put_in_pack(self):
        for rec in self:
            exsist_total_weight = 0
            product_ids = rec.picking_id.move_line_ids.filtered(lambda m:
                          float_compare(m.qty_done, 0.0,precision_rounding=m.product_uom_id.rounding) > 0
                          and not m.result_package_id).mapped('product_id').filtered(lambda s: s.weight < 1)
            for ml in rec.picking_id.move_line_ids:
                qty = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
                exsist_total_weight += qty * ml.product_id.weight

            if product_ids and rec.shipping_weight <= exsist_total_weight :
                raise UserError(
                    _("Please enter the weight for product(s) %s OR enter Shipping Weight more than existing" % '\n,'.join(x.display_name for x in product_ids)))
            if not rec.product_length or not rec.product_width or not rec.product_height:
                raise UserError(_("Please enter the respective L X W X H"))
            rec.picking_id.write({
                'total_weight': rec.shipping_weight,
                'total_length': rec.product_length,
                'total_width': rec.product_width,
                'total_height': rec.product_height
            })
            self.env.context = dict(self.env.context)
            self.env.context.update({'width': rec.product_width,'length': rec.product_length,'height':rec.product_height})

        return super().action_put_in_pack()
