from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"


    total_product_uom_qty = fields.Float('Total Quantity', compute='_compute_total_quantity', readonly=True, store=True)


    @api.depends('order_line')
    def _compute_total_quantity(self):
        # product_inventory_volume = self.env['ir.config_parameter'].sudo().get_param('sale_stock_extend.product_inventory_volume')
        for rec in self:
            total_qty = 0
            for line in rec.order_line:
                if line.product_id.detailed_type != 'service':
                    total_qty += line.product_uom_qty
                # # if line.product_id.volume < int(product_inventory_volume) and line.product_id.categ_id.name != 'Part':
                # total_qty += line.product_uom_qty

            rec.total_product_uom_qty = total_qty

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_single_ship = fields.Boolean(string="Single Ship",default=False)
    route_id = fields.Many2one('stock.route', string='Route', domain=[('sale_selectable', '=', True)], ondelete='restrict', check_company=True, copy=False)
