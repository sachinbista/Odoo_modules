# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    delivery_section = fields.Boolean(string="Delivery Section")
    service_id = fields.Many2one('product.product')
    service_line = fields.Many2one('sale.order.line', compute="_get_service_line_id")

    @api.depends('delivery_section')
    def _get_service_line_id(self):
        for line in self:
            line_id = False
            if line.service_id:
                service_line_ids = line.order_id.order_line.filtered(lambda l: l.product_id.id == line.service_id.id)
                if service_line_ids:
                    line_id = service_line_ids[0]
            line.service_line = line_id

    def unlink(self):
        for line in self:
            has_line = any(line.service_id == order_line.service_id for order_line in line.order_id.order_line if
                           line != order_line)
            if not has_line:
                line.service_line.unlink()
                self -= line.service_line
            else:
                line.service_line.product_uom_qty -= line.product_uom_qty
        return super(SaleOrderLine, self).unlink()

    def _is_service_line(self):
        return self.product_template_id.is_group

    def write(self, vals):
        product_uom_qty = vals.get('product_uom_qty')
        for line in self:
            if line.service_id and "product_uom_qty" in vals and product_uom_qty:
                difference = product_uom_qty - line.product_uom_qty
                line.service_line.product_uom_qty += difference
        return super().write(vals)
