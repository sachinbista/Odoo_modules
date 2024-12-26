# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import AccessDenied


class Picking(models.Model):
    _inherit = 'stock.picking'

    def action_reserve(self):
        for x in self:
            on_hold = x.sale_on_hold()
            if on_hold:
                return on_hold
        return super(Picking, self).action_reserve()


    def button_validate(self):
        for x in self:
            on_hold = x.sale_on_hold()
            if on_hold:
                return on_hold
        return super(Picking, self).button_validate()



    def sale_on_hold(self):
        user = self.env.user
        credit_manager_group = self.env.ref('ob_customer_credit_limit.customer_credit_limit_manager')
        if self.sale_id and self.sale_id.on_hold:
            if credit_manager_group in user.groups_id:
                return False

            context = dict(self.env.context or {})
            context['default_stock_picking_id'] = self.id
            view_id = self.env.ref('ob_customer_credit_limit.view_warning_wizard_form')
            context['message'] = (self.partner_id.credit_warning_message or
                                  "Customer credit limit exceeded, Do You want to continue?")
            if not self._context.get('warning'):
                return {
                    'name': 'Warning',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'warning.wizard',
                    'view_id': view_id.id,
                    'target': 'new',
                    'context': context,
                }
        return