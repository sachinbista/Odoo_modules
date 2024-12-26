# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_credit_manager_group(self):
        return self.env.ref('bista_customer_credit_limit.customer_credit_limit_manager')

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for order in self:
            if 'order_line' in vals or 'amount_total' in vals:
                credit_manager_group = self._get_credit_manager_group()
                if not credit_manager_group or credit_manager_group.id not in self.env.user.groups_id.ids:
                    if order.amount_total and order.amount_total > order.credit_blocking_threshold and order.partner_id.credit_check:
                        self._notify_credit_managers(order)

        return res

    def _notify_credit_managers(self, sale_order):
        credit_manager_group = self._get_credit_manager_group()
        if not credit_manager_group:
            return

        credit_manager_users = credit_manager_group.users
        if not credit_manager_users:
            return

        subject = _("Customer Credit Exceeded: %s") % sale_order.partner_id.name
        body = _(
            """
            <p>Dear Credit Manager,</p>
            <p>The following sale order has been created by user <strong>%s</strong> 
            for customer <strong>%s</strong>, exceeding the credit blocking threshold</p>
            <ul>
                <li>Sale Order: %s</li>
                <li>Sale Order Amount: %s</li>
                <li>Credit Blocking Threshold: %s</li>
            </ul>
            <p>Please review this order.</p>
            """ % (
                self.env.user.name,
                sale_order.partner_id.name,
                sale_order.name,
                sale_order.amount_total,
                sale_order.credit_blocking_threshold,
            )
        )

        template_id = self.env.ref(
            'bista_customer_credit_limit.email_template_to_notify_users').id
        template = self.env['mail.template'].browse(template_id)
        template.send_mail(self.id,
                           force_send=True,
                           email_values={
                               'subject': subject,
                               'email_to': ",".join(user.partner_id.email for user in credit_manager_users if user.partner_id.email),
                               'body_html': body,
                           })

        # mail_values = {
        #     'subject': subject,
        #     'body_html': body,
        #     'email_to': ",".join(user.partner_id.email for user in credit_manager_users if user.partner_id.email),
        # }
        # self.env['mail.mail'].create(mail_values).send()
