from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime

class GoflowHoldOrderWiz(models.TransientModel):
    _name = "goflow.hold.order.wiz"
    _description = "goflow.hold.order.wiz"
    
    reason = fields.Text("")

    def hold_order(self):
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if sale_order:
            sale_order.goflow_hold_reason = self.reason
            sale_order.set_order_on_hold()