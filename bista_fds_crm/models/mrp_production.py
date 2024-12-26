from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    customer_po_number = fields.Char(string="Customer PO #")


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        res = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
        if origin:
            sale_order = self.env['sale.order'].search([('name', '=', origin)], limit=1)
            if sale_order:
                res['customer_po_number'] = sale_order.client_order_ref
        return res

