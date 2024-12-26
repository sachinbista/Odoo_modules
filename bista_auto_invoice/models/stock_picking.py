# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockInherit(models.Model):
    _inherit = 'stock.picking'
    inv_created = fields.Boolean(string="Invoice Created", copy=False, default=False)

    def _prepare_invoice_values(self, order):
        want_to_send = False
        if not order.shopify_order_id and not order.rithum_config_id:
            want_to_send = True
        invoice_vals = {
            'ref': order.client_order_ref,
            'move_type': 'out_invoice',
            'invoice_origin': order.name,
            'invoice_user_id': order.user_id.id,
            'narration': order.note,
            'partner_id': order.partner_invoice_id.id,
            'fiscal_position_id': order.fiscal_position_id and order.fiscal_position_id._get_fiscal_position(
                order.partner_id).id or False,
            'partner_shipping_id': order.partner_shipping_id.id,
            'currency_id': order.pricelist_id.currency_id.id,
            'payment_reference': order.reference,
            'invoice_payment_term_id': order.payment_term_id.id,
            'partner_bank_id': order.company_id.partner_id.bank_ids[:1].id,
            'team_id': order.team_id.id,
            'campaign_id': order.campaign_id.id,
            'medium_id': order.medium_id.id,
            'source_id': order.source_id.id,
            'picking_id': self.id,
            'want_to_send_email':want_to_send,
        }
        return invoice_vals

    def post_non_invoiced_message(self, order):
        chatter_group_id = self.company_id.chatter_group_id
        if chatter_group_id:
            channel_msg = (
                f"<br/>Sales Order {order.name} has a delivery of products that were not invoiced and paid for.")
            chatter_group_id.message_post(
                body=_(channel_msg),
                message_type="notification", subtype_xmlid="mail.mt_comment"
            )

    def has_non_invoiced_lines(self):
        has_non_invoiced_lines = False
        for rec in self:
            sale_id = rec.sale_id
            if rec.origin and not sale_id:
                sale_id = self.env['sale.order'].search([('name', '=', rec.origin)])

            if rec.picking_type_code == 'outgoing' and not rec.inv_created and sale_id and sale_id.company_id.enable_auto_invoice and (
                    not sale_id.payment_term_id or (sale_id.payment_term_id and not sale_id.payment_term_id.auto_invoice)):
                for line in sale_id.order_line:
                    if line.invoice_status != 'invoiced':
                        has_non_invoiced_lines = True
                        break
        return has_non_invoiced_lines

    def button_validate(self):
        # context = dict(self._context) or {}
        # has_non_invoiced_lines = self.has_non_invoiced_lines()
        # if context.get('show_confirm', False) and has_non_invoiced_lines:
        #     self.post_non_invoiced_message(self.sale_id)
        #     return {
        #         'name': _('Non Invoiced Warning'),
        #         'type': 'ir.actions.act_window',
        #         'view_mode': 'form',
        #         'res_model': 'transfer.validate.confirm',
        #         'res_id': self.env['transfer.validate.confirm'].create({'picking_id': self.id}).id,
        #         'target': 'new'
        #     }

        res = super(StockInherit, self).button_validate()

        # if isinstance(res, dict) and res.get("res_model") == "stock.immediate.transfer":
        #     return res
        # inv_mail_template = self.env.ref('account.email_template_edi_invoice',
        #                                  raise_if_not_found=False)
        # sale_order_obj = self.env['sale.order']
        # for picking in self:
        #     sale_id = picking.sale_id
        #     if picking.origin and not sale_id:
        #         sale_id = sale_order_obj.search([('name', '=', picking.origin)])
        #     if picking.carrier_id or picking.carrier_tracking_ref:
        #         if not picking.inv_created and sale_id:
        #             if sale_id.company_id.enable_auto_invoice:
        #                 if sale_id.payment_term_id and sale_id.payment_term_id.auto_invoice:
        #                     delivery_lines = self.env['sale.order.line'].search(
        #                         [('order_id', '=', sale_id.id), ('product_id.detailed_type', '=', 'service'),
        #                          ('qty_invoiced', '=', 0.0)])
        #                     invoice_vals = self._prepare_invoice_values(sale_id)
        #                     line_list = []
        #                     invoice_count = sale_id.invoice_count
        #                     for line in sale_id.order_line:
        #                         if line.invoice_status == 'invoiced':
        #                             continue
        #
        #                         move_line_id = self.env['stock.move.line'].sudo().search(
        #                             [('picking_id', '=', picking.id),
        #                              ('product_id', '=', line.product_id.id),
        #                              ('move_id.sale_line_id', '=', line.id)])
        #
        #                         if move_line_id:
        #                             line_dict = line._prepare_invoice_line()
        #                             qty_to_invoice = 0
        #                             for m_id in move_line_id:
        #                                 qty_to_invoice += m_id.qty_done
        #                             line_dict.update({'quantity': qty_to_invoice})
        #                             line_list.append((0, 0, line_dict))
        #                     for delivery_line in delivery_lines:
        #                         delivery_line_dict = delivery_line._prepare_invoice_line()
        #                         delivery_line_dict.update({'quantity': delivery_line.product_uom_qty})
        #                         line_list.append((0, 0, delivery_line_dict))
        #                                 # if invoice_count == 0:
        #                                 #     if line_dict['quantity'] > 0 and (
        #                                 #             m_id or line.is_delivery or line.product_id.type == "service"):
        #                                 #         line_list.append((0, 0, line_dict))
        #                                 # else:
        #                                 #     if line_dict['quantity'] > 0 and m_id:
        #                                 #         line_list.append((0, 0, line_dict))
        #                     if line_list and picking.picking_type_code == 'outgoing':
        #                         invoice_vals['invoice_line_ids'] = line_list
        #                         invoice = self.env['account.move'].sudo().create(invoice_vals)
        #                         invoice.action_post()
        #                         lang = False
        #                         if inv_mail_template:
        #                             lang = inv_mail_template._render_lang(invoice.ids)[invoice.id]
        #                         emails = set(partner['email'] for partner in picking.sale_id.partner_id.child_ids if
        #                                      partner.email)
        #                         inv_mail_template.write({'email_to': ','.join(emails)})
        #
        #                         ctx = dict(
        #                             mark_invoice_as_sent=True,
        #                             active_ids=invoice.ids,
        #                             custom_layout="mail.mail_notification_paynow",
        #                             model_description=invoice.with_context(lang=lang).type_name,
        #                             force_email=True,
        #                             default_res_model='account.move',
        #                             default_use_template=bool(inv_mail_template))
        #                         values = {
        #                             'model': 'account.move',
        #                             'res_id': invoice.id,
        #                             'template_id': inv_mail_template and inv_mail_template.id or False,
        #                             'composition_mode': 'comment',
        #                         }
        #                         # if invoice.payment_state != "not_paid":
        #                         wizard = self.env['account.invoice.send'].with_context(ctx).create(values)
        #                         wizard._compute_composition_mode()
        #                         # wizard.onchange_template_id()
        #                         # wizard.onchange_is_email()
        #                         wizard._send_email()
        #                         # Empty email_to to prevent sending mail to wrong people
        #                         inv_mail_template.write({'email_to': ""})
        #                         picking.inv_created = True
        #                 else:
        #                     if picking.picking_type_code == 'outgoing':
        #                         if has_non_invoiced_lines:
        #                             self.post_non_invoiced_message(sale_id)
        #                             # self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
        #                             #     'title': _("Warning"),
        #                             #     'sticky': False,
        #                             #     'message': _('Some of the products you are attempting to deliver have not been fully invoiced and fully paid for. And message was logged to the group.')
        #                             # })
        return res

    def _pre_action_done_hook(self):
        for picking in self:
            context = dict(self._context) or {}
            has_non_invoiced_lines = picking.has_non_invoiced_lines()
            if context.get('show_confirm', False) and has_non_invoiced_lines:
                self.post_non_invoiced_message(picking.sale_id)
                return {
                    'name': _('Non Invoiced Warning'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'transfer.validate.confirm',
                    'res_id': self.env['transfer.validate.confirm'].create({'picking_id': picking.id}).id,
                    'target': 'new'
                }
        res = super()._pre_action_done_hook()
        return res

    def _action_done(self):
        has_non_invoiced_lines = self.has_non_invoiced_lines()
        # if context.get('show_confirm', False) and has_non_invoiced_lines:
        #     self.post_non_invoiced_message(self.sale_id)
        #     return {
        #         'name': _('Non Invoiced Warning'),
        #         'type': 'ir.actions.act_window',
        #         'view_mode': 'form',
        #         'res_model': 'transfer.validate.confirm',
        #         'res_id': self.env['transfer.validate.confirm'].create({'picking_id': self.id}).id,
        #         'target': 'new'
        #     }

        res = super()._action_done()

        inv_mail_template = self.env.ref('account.email_template_edi_invoice',
                                         raise_if_not_found=False)
        sale_order_obj = self.env['sale.order']
        for picking in self:
            sale_id = picking.sale_id
            if picking.origin and not sale_id:
                sale_id = sale_order_obj.search([('name', '=', picking.origin)])
            if picking.carrier_id or picking.carrier_tracking_ref:
                if not picking.inv_created and sale_id:
                    if sale_id.company_id.enable_auto_invoice:
                        if sale_id.payment_term_id and sale_id.payment_term_id.auto_invoice:
                            delivery_lines = self.env['sale.order.line'].search(
                                [('order_id', '=', sale_id.id), ('product_id.detailed_type', '=', 'service'),
                                 ('qty_invoiced', '=', 0.0)])
                            invoice_vals = self._prepare_invoice_values(sale_id)
                            line_list = []
                            invoice_count = sale_id.invoice_count
                            for line in sale_id.order_line:
                                if line.invoice_status == 'invoiced':
                                    continue

                                move_line_id = self.env['stock.move.line'].sudo().search(
                                    [('picking_id', '=', picking.id),
                                     ('product_id', '=', line.product_id.id),
                                     ('move_id.sale_line_id', '=', line.id)])

                                if move_line_id:
                                    line_dict = line._prepare_invoice_line()
                                    qty_to_invoice = 0
                                    for m_id in move_line_id:
                                        qty_to_invoice += m_id.qty_done
                                    line_dict.update({'quantity': qty_to_invoice})
                                    line_list.append((0, 0, line_dict))
                            for delivery_line in delivery_lines:
                                delivery_line_dict = delivery_line._prepare_invoice_line()
                                delivery_line_dict.update({'quantity': delivery_line.product_uom_qty})
                                line_list.append((0, 0, delivery_line_dict))
                                # if invoice_count == 0:
                                #     if line_dict['quantity'] > 0 and (
                                #             m_id or line.is_delivery or line.product_id.type == "service"):
                                #         line_list.append((0, 0, line_dict))
                                # else:
                                #     if line_dict['quantity'] > 0 and m_id:
                                #         line_list.append((0, 0, line_dict))
                            if line_list and picking.picking_type_code == 'outgoing':
                                invoice_vals['invoice_line_ids'] = line_list
                                invoice = self.env['account.move'].sudo().create(invoice_vals)
                                invoice.action_post()
                                lang = False
                                if inv_mail_template:
                                    lang = inv_mail_template._render_lang(invoice.ids)[invoice.id]
                                emails = set(partner['email'] for partner in picking.sale_id.partner_id.child_ids if
                                             partner.email)
                                inv_mail_template.write({'email_to': ','.join(emails)})

                                ctx = dict(
                                    mark_invoice_as_sent=True,
                                    active_ids=invoice.ids,
                                    custom_layout="mail.mail_notification_paynow",
                                    model_description=invoice.with_context(lang=lang).type_name,
                                    force_email=True,
                                    default_res_model='account.move',
                                    default_use_template=bool(inv_mail_template))
                                values = {
                                    'model': 'account.move',
                                    'res_id': invoice.id,
                                    'template_id': inv_mail_template and inv_mail_template.id or False,
                                    'composition_mode': 'comment',
                                }
                                # if invoice.payment_state != "not_paid":
                                wizard = self.env['account.invoice.send'].with_context(ctx).create(values)
                                wizard._compute_composition_mode()
                                # wizard.onchange_template_id()
                                # wizard.onchange_is_email()
                                wizard._send_email()
                                # Empty email_to to prevent sending mail to wrong people
                                inv_mail_template.write({'email_to': ""})
                                picking.inv_created = True
                        else:
                            if picking.picking_type_code == 'outgoing':
                                if has_non_invoiced_lines:
                                    self.post_non_invoiced_message(sale_id)
                                    # self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                                    #     'title': _("Warning"),
                                    #     'sticky': False,
                                    #     'message': _('Some of the products you are attempting to deliver have not been fully invoiced and fully paid for. And message was logged to the group.')
                                    # })
        return res

