from odoo import models, fields

class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_purchase_order(self, company_id, origins, values):
        vals =  super()._prepare_purchase_order(company_id, origins, values)
        if origins:
            sale_order = self.env['sale.order'].search([('name', '=', list(origins)[0])], limit=1)
            if sale_order:
                vals['customer_po_id'] = sale_order.partner_id.id
                vals['customer_po_number'] = sale_order.client_order_ref
                vals['origin'] = sale_order.name
        return vals


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    customer_po_id = fields.Many2one('res.partner', string="Customer")
    customer_po_number = fields.Char(string="Customer PO #")