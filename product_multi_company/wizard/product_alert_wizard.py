from odoo import models, fields


class ProductAlertWizard(models.TransientModel):
    _name = "product.alert.wizard"
    _description = "product Alert Wizard"

    name = fields.Char(string="Message", readonly=True)

    def action_continue(self):
        active_id = self._context.get("active_id")
        if active_id:
            product = self.env['product.template'].browse(active_id)
            return product
