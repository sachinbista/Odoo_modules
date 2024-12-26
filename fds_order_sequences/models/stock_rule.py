from odoo import _, api, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # def _prepare_purchase_order(self, company_id, origins, values):
    #     """Update PO's name to include SO'name."""
    #     vals = super(StockRule, self)._prepare_purchase_order(company_id, origins, values)
    #     values = values[0]
    #     if (group := values.get('group_id')) and (so := group.sale_id):
    #         po_sequence = self.env['ir.sequence'].get_by_code('purchase.order')
    #         po_count = so.purchase_order_count
    #         vals['name'] = f"{po_sequence and po_sequence.prefix}/{so.name}/{po_count + 1}"
    #     return vals
