from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    customer_type = fields.Many2one(
        string="Customer Type",
        comodel_name='res.partner.category',
        compute='_compute_customer_type',
        store=True , copy=False
    )
    external_origin = fields.Selection(related='order_id.external_origin',string='Order From', store=True, copy=False )
    date_order = fields.Datetime(related='order_id.date_order', string="Order Date", store=True, copy=False)
    goflow_store_id = fields.Many2one(related="order_id.goflow_store_id", store=True, copy=False)


    @api.depends('order_partner_id.category_id')
    def _compute_customer_type(self):
        for line in self:
            line.customer_type = line.order_partner_id.category_id and line.order_partner_id.category_id[0] or False
