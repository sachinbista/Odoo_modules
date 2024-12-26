# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,
                                          related='company_id.currency_id')
    credit_blocking_threshold = fields.Monetary(related="partner_id.credit_blocking_threshold")
    on_hold = fields.Boolean(copy=False)

    def action_confirm(self):
        """
            Check the partner credit limit and existing due of the partner
            before confirming the order. The order is only blocked if existing
            due is greater than blocking limit of the partner.
        """
        if len(self) > 1:
            credit_check = any(order.partner_id.credit_check for order in self)
            if credit_check:
                raise UserError("Some orders require credit check. Please process the sales order individually")

        partner = self.partner_id
        if partner.credit_check and not self.env.context.get("skip_warning"):

            context = dict(self.env.context or {})
            context['default_sale_id'] = self.id
            view_id = self.env.ref('ob_customer_credit_limit.view_warning_wizard_form')

            sale_value = sum(line.price_subtotal for line in self.order_line)

            user = self.env.user
            credit_manager_group = self.env.ref('ob_customer_credit_limit.customer_credit_limit_manager')

            if partner.credit_blocking_threshold < sale_value:
                message = (partner.credit_warning_message or f"Credit Blocking limit reached! {self.name}")
                if credit_manager_group in user.groups_id:
                    context['message'] = (partner.credit_warning_message or
                                          "Customer credit limit exceeded, Want to continue?")
                    return {
                        'name': 'Blocking Limit',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'warning.wizard',
                        'view_id': view_id.id,
                        'target': 'new',
                        'context': context,
                    }
                else:
                    raise UserError(message)

            elif partner.credit_warning_threshold < sale_value:
                context['message'] = (partner.credit_warning_message or
                                      "Customer credit limit exceeded, Want to continue?")
                return {
                    'name': 'Warning Limit',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'warning.wizard',
                    'view_id': view_id.id,
                    'target': 'new',
                    'context': context,
                }
        return super(SaleOrder, self).action_confirm()
