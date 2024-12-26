from odoo import fields, models, _, api
from odoo.exceptions import UserError


class ProductAllocation(models.Model):
    _name = 'product.allocation'
    _rec_name = 'product_id'
    _description = 'Product Allocation'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=False)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    allocated_qty = fields.Float(string="Allocation Quantity", required=True)
    customer_group_id = fields.Many2one('partner.group', string='Groups')
    current_allocation_qty = fields.Float(string="processed Allocation", compute='_compute_current_allocation_qty')
    remaining_qty = fields.Float(string="Remaining Quantity")

    def _compute_current_allocation_qty(self):
        """Compute the current allocation quantity"""
        sale_line_obj = self.env['sale.order.line'].sudo()
        for rec in self:
            rec.current_allocation_qty = 0.0
            if rec.partner_id:
                lines = sale_line_obj.search([
                    ('product_id', '=', rec.product_id.id),
                    ('order_id.partner_id', '=', rec.partner_id.id),
                    ('order_id.state', 'in', ['sale'])])
            else:
                lines = sale_line_obj.search([
                    ('product_id', '=', rec.product_id.id),
                    ('order_id.partner_id.group_id', '=', rec.customer_group_id.id),
                    ('order_id.state', 'in', ['sale'])])
            for line in lines:
                rec.current_allocation_qty += line.product_uom_qty
            rec.remaining_qty = rec.allocated_qty - rec.current_allocation_qty
