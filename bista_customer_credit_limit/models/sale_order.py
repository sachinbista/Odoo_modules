# -*- coding: utf-8 -*-
from odoo import models, fields,api,_
from odoo.exceptions import UserError

from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,related='company_id.currency_id')
    credit_blocking_threshold = fields.Monetary(related="partner_id.credit_blocking_threshold")
    on_hold = fields.Boolean(copy=False)
    block_order = fields.Boolean(string='Credit held',copy=False)
    flag = fields.Boolean(default=False)
    update_flag = fields.Boolean('update_flag')
    # warning_boolean = fields.Boolean('Warning Message')
    warning_message = fields.Html(string='Warning')

    credit_warning_threshold = fields.Monetary(related="partner_id.credit_warning_threshold")

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order.warning_message = ''
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            sale_warning_message = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_waring_message')
            sale_blocking_message = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_blocking_message')

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax
            order.partner_id._compute_credit_threshold()
            if order.state == 'sale' and order.partner_id.credit_check:
                group = self.env.ref('bista_customer_credit_limit.customer_credit_limit_manager')
                users_in_group = self.env['res.users'].search([('groups_id', 'in', group.id)])
                if users_in_group:
                    order.partner_id._compute_credit_threshold()
                    if order.partner_id.credit_warning_threshold < 0:
                        order.flag = True
                    if order.partner_id.credit_blocking_threshold < 0 :
                        order.flag = True
                else:
                    if order.partner_id.credit_warning_threshold < 0:
                        if order.partner_id.credit_warning_message:
                            order.warning_message = order.partner_id.credit_warning_message
                        elif sale_warning_message:
                            order.warning_message = sale_warning_message
                        else:
                            order.warning_message = "Warning Limit Is Over"
                    if order.partner_id.credit_blocking_threshold < 0 :
                        raise UserError("Only credit managers can modify this sales order.")
                        order.warning_message = ''
                    else:
                        order.partner_id._compute_credit_threshold()


    def action_confirm(self):
        """
            Check the partner credit limit and existing due of the partner
            before confirming the order. The order is only blocked if existing
            due is greater than blocking limit of the partner.
        """
        if self.partner_id.lock_all_transaction:
            raise ValidationError(
                _("All Transactions are locked."))

        if len(self) > 1:
            credit_check = any(order.partner_id.credit_check for order in self)
            if credit_check:
                raise UserError("Some orders require credit check. Please process the sales order individually")

        sale_blocking_message = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_blocking_message')
        sale_warning_message = self.env['ir.config_parameter'].sudo().get_param('base_setup.default_waring_message')

        partner = self.partner_id
        if not self.env.context.get("skip_warning"):
            context = dict(self.env.context or {})
            context['default_sale_id'] = self.id
            view_id = self.env.ref('bista_customer_credit_limit.view_warning_wizard_form')

            sale_value = sum(line.price_subtotal for line in self.order_line)

            user = self.env.user
            credit_manager_group = self.env.ref('bista_customer_credit_limit.customer_credit_limit_manager')
            if partner.credit_blocking_threshold < sale_value :
                if partner.credit_blocking != 0.0 :
                    message = (partner.credit_blocking_message or f"Credit Blocking limit reached! {self.name}")

                    if credit_manager_group in user.groups_id:

                        if partner.credit_blocking_message:
                            context['message'] = (partner.credit_blocking_message or
                                                  "Customer credit limit exceeded, Want to continue?")

                        else:
                            context[
                                'message'] = sale_blocking_message or "Customer credit limit exceeded, Want to continue?"

                        context['default_sale_id'] = self.id

                        view_id = self.env.ref('bista_customer_credit_limit.view_blocking_wizard_form')
                        return {
                            'name': 'Blocking Limit',
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'res_model': 'blocking.wizard',
                            'view_id': view_id.id,
                            'target': 'new',
                            'context': context,
                        }
                    elif(partner.credit_check):
                        context['message'] = (partner.credit_blocking_message or
                                              "Customer credit limit exceeded, Want to continue?")

                        view_id = self.env.ref('bista_customer_credit_limit.view_warning_wizard_custom_form')
                        return {
                            'name': 'Blocking Limit',
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'res_model': 'warning.wizard.custom',
                            'view_id': view_id.id,
                            'target': 'new',
                            'context': context,
                        }
                else:
                    pass

            elif partner.credit_warning_threshold < sale_value:
                if partner.credit_warning != 0:
                    if partner.credit_warning_message:
                        context['message'] = (partner.credit_warning_message or
                                              "Customer credit limit exceeded, Want to continue?")
                    else:
                        context['message'] = sale_warning_message or "Customer credit limit exceeded, Want to continue?"
                    return {
                        'name': 'Warning Limit',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'warning.wizard',
                        'view_id': view_id.id,
                        'target': 'new',
                        'context': context,
                    }
                else:
                    pass

        return super(SaleOrder, self).action_confirm()

