from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_po_number = fields.Char(string="Customer PO #", compute="_compute_sale_order_customer_po")

    def _compute_sale_order_customer_po(self):
        for invoice in self:
            sale_orders = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
            invoice.customer_po_number = sale_orders  and ', '.join(set(sale_orders.filtered(lambda l: l.client_order_ref != False).mapped('client_order_ref'))) or False
