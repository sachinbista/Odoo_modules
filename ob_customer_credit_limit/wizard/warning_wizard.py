# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError

class WarningWizard(models.TransientModel):
    _name = "warning.wizard"
    _description = "Warning Wizard"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)
    sale_id = fields.Many2one('sale.order', string="Sale Order")
    stock_picking_id = fields.Many2one("stock.picking")


    def action_confirm(self):
        if self.sale_id:
            self.sale_id.with_context(skip_warning=True).action_confirm()
        elif self.stock_picking_id:
            raise UserError("No group is allowed to perform this action")

