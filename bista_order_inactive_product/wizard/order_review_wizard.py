from odoo import models, fields


class OrderReviewWizard(models.TransientModel):
    _name = "order.review.wizard"
    _description = "Order Review Wizard"

    name = fields.Text(string="Message", readonly=True)

    def action_continue(self):
        active_id = self._context.get("active_id")
        if active_id:
            order = self.env['sale.order'].browse(active_id)
            order.with_context(skip_rule = True).action_confirm()
