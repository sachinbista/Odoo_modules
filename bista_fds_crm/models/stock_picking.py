
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    customer_po_number = fields.Char(string="Customer PO #", related="sale_id.client_order_ref")
    sale_user_id = fields.Many2one('res.users', 'Sales Res', related="sale_id.user_id")

class AccountMoveLine(models.Model):
    _inherit = 'stock.move.line'

    description_picking = fields.Text(related="move_id.description_picking")


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values, po):
        res = super(PurchaseOrderLine, self)._prepare_purchase_order_line_from_procurement(product_id, product_qty, product_uom, company_id, values, po)
        if 'product_description_variants' in values:
            res['name'] = values.get('product_description_variants', '')
        return res