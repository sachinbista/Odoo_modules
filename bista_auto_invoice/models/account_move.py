# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
import logging
from odoo import fields, models, api, _
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"


    is_payment_not_created = fields.Boolean(
        string="Payment Not Created",
        readonly=True,
        default=False,
        store=True,
        compute='_compute_is_payment_not_created'
    )

    @api.depends('payment_state')
    def _compute_is_payment_not_created(self):
        for record in self:
            if record.payment_state in ['in_payment', 'paid']:
                record.is_payment_not_created = False
            else:
                record.is_payment_not_created = True

    # payment_success_message_posted = fields.Boolean(
    #     string="Payment Success Message Posted", default=False
    # )
    # order_id = fields.Many2one('sale.order')
    # manual_payment_creation = fields.Boolean(string="Manual Payment Creation",default=False)

    # @api.depends('payment_state')
    # def _check_payment_state(self):
    #     for record in self:
    #         try:
    #             if record.payment_state == 'in_payment' or 'paid' and self.order_id:
    #                 record.is_payment_not_created = False
    #                 if not record.payment_success_message_posted and not self.manual_payment_creation:
    #                     record._post_payment_success_message(record.order_id)
    #                     record.payment_success_message_posted = True
    #             else:
    #                 if record.payment_state != 'in_payment' or 'paid':
    #                     record.is_payment_not_created = True
    #
    #                 record.payment_success_message_posted = False
    #         except ValueError as e:
    #             _logger.error(f"Error in _check_payment_state: {e}")

    def _post_payment_success_message(self, sale_order):
        payment_failure_channel_id = self.env['ir.config_parameter'].sudo().get_param(
            'bista_auto_invoice.payment_failure_channel'
        )
        if payment_failure_channel_id:
            try:
                channel = self.env['discuss.channel'].browse(int(payment_failure_channel_id))
                sales_person = sale_order.user_id.name
                order_number = sale_order.name
                delivery_numbers = ", ".join(sale_order.picking_ids.mapped('name'))
                customer_name = sale_order.partner_id.name
                message = _(
                    "<b>Payment is created.</b><br/>"
                    "<b>Sales person:</b> %s<br/>"
                    "<b>Sale order:</b> %s<br/>"
                    "<b>Delivery number:</b> %s<br/>"
                    "<b>Customer name:</b> %s"
                    "</div>"
                ) % (sales_person, order_number, delivery_numbers, customer_name)

                channel.message_post(body=Markup(message), message_type="comment", subtype_xmlid="mail.mt_comment")
            except ValueError as e:
                _logger.error(f"Error posting payment success message: {e}")

    def action_register_payment(self):
        res = super().action_register_payment()
        context = res.get('context', {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        parent_partner = self.partner_id.commercial_partner_id
        sale_order = self.env['sale.order'].search([('invoice_ids.name', '=', self.name)], limit=1)
        context = res.get('context', {})
        context['is_manual_payment'] = True
        if len(parent_partner.payment_token_ids) == 1:
            default_payment_token = parent_partner.payment_token_ids
        else:
            default_payment_token = parent_partner.payment_token_ids.filtered(lambda token: token.default_payment_token)
        failure_reason = []
        try:
            if not default_payment_token:
                failure_reason.append("default payment token Not available")
            if not self.env.context.get('auto_inv_payment'):
                failure_reason.append("Auto invoice payment Is Not Enabled")

            if active_model in ['account.move.line',
                                'account.move'] and active_ids and default_payment_token and self.env.context.get('auto_inv_payment'):
                if active_model == 'account.move.line':
                    journal_id = self.env['payment.provider'].search([('code', '=', 'authorize')], limit=1)
                    payment_provider = self.env['account.payment.method.line'].search([('name', '=', 'Authorize.net')],
                                                                                      limit=1)
                    payment_register = self.env['account.payment.register'].with_context(active_model=active_model,
                                                                                         active_ids=active_ids).create({
                        'journal_id': journal_id.journal_id.id,
                        'payment_method_line_id': payment_provider.id,
                        'payment_authorize': True,
                        'payment_token_id': default_payment_token.id,
                    })
                    payment_register.action_create_payments()
                    transaction = self.env['payment.transaction'].search([('reference', '=', self.name)],
                                                                         limit=1)
                    # transaction.state_message = "failure test massage"
                    if transaction and transaction.state != 'done':
                        if transaction.state_message:
                            failure_reason.append(transaction.state_message)
                        self._post_payment_failure_message(sale_order, failure_reason)
                    # self._post_payment_success_message(sale_order)
                    self.is_payment_not_created = False

            elif(self.env.context.get('auto_inv_payment')):
                self._post_payment_failure_message(sale_order,failure_reason)

        except Exception as e:
            _logger.error(f"Error creating payment: {e}")

        return res

    def _post_payment_failure_message(self, sale_order,failure_reason):
        payment_failure_channel_id = self.env['ir.config_parameter'].sudo().get_param(
            'bista_auto_invoice.payment_failure_channel') or ''
        self.is_payment_not_created = True
        if payment_failure_channel_id:
            try:
                channel = self.env['discuss.channel'].browse(int(payment_failure_channel_id))
                sales_person = sale_order.user_id.name
                order_number = sale_order.name
                delivery_numbers = ", ".join(
                    sale_order.picking_ids.mapped('name'))
                customer_name = sale_order.partner_id.name
                failure_reason_message = ", ".join(failure_reason) if failure_reason else " "
                message = _(
                    "<b>Payment is not created.</b><br/>"
                    "<b>Sales person:</b> %s<br/>"
                    "<b>Sale order:</b> %s<br/>"
                    "<b>Delivery number:</b> %s<br/>"
                    "<b>Customer name:</b> %s<br/>"
                    "<b>Reason:</b> %s"
                    "</div>"
                ) % (sales_person, order_number, delivery_numbers, customer_name, failure_reason_message)
                channel.message_post(body=Markup(message), message_type="comment", subtype_xmlid="mail.mt_comment")
            except ValueError:
                pass