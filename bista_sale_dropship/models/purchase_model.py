# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sh_sale_order_id = fields.Many2one(
        "sale.order", string="Sale Order", readonly=True, copy=False)

    type_of_purchase = fields.Selection([
        ('internal', 'Internal'),
        ('dropship', 'Dropship')],
        string="Purchase Type", readonly=True, default='internal', copy=False)

    def copy(self, default=None):
        self.ensure_one()  # Ensure that this method is called on a single record
        # Perform additional checks before copying
        if self.type_of_purchase == 'dropship' and self.sh_sale_order_id:
            # Customize or raise a warning here
            raise UserError(_("You can't copy a dropship record with a linked sale order."))

        # Call the parent copy method to perform the actual copy
        return super(PurchaseOrder, self).copy(default)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if self.order_id.type_of_purchase == "dropship":
            res.update({'sale_line_id': self.sale_line_id.id if self.sale_line_id else False})
        return res
