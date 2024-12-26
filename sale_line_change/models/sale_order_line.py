from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # In 14, this field exists, but isn't stored and is merely related to the
    # order's warehouse_id, it is only used in computation of availability
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
                                   compute=None, related=None, store=True, copy=False)

    def _prepare_procurement_values(self, group_id=False):
        vals = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        if self.warehouse_id:
            vals.update({'warehouse_id': self.warehouse_id})
        # if self.date_planned:
        #     vals.update({'date_planned': self.date_planned})
        # elif self.order_id.date_planned:
        #     vals.update({'date_planned': self.order_id.date_planned})
        return vals