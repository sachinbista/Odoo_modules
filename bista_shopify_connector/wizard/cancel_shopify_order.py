from odoo import models, fields


class CancelShopifyOrder(models.TransientModel):
    _name = 'cancel.shopify.order'
    _description = "cancel.shopify.order"

    order_id = fields.Many2one('sale.order', string='Sale Order',
                               default=lambda self: self.env.context.get('active_id', None), )

    def action_cancel_sale(self):
        self.order_id.with_context(disable_cancel_warning=True).action_cancel()
