from odoo import models, api,fields,_


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_discount(self):
        res = super()._compute_discount()
        discount = self.order_id.partner_id.discount
        if discount > 0.0:
            for line in self:
                if line.product_id:
                    line.discount = discount
        return res

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res['is_delivery'] = self.is_delivery
        return res