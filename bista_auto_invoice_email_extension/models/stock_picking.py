# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class Picking(models.Model):
    _inherit = 'stock.picking'



    # def _action_done(self):
    #     res = super(Picking, self)._action_done()
    #     email_template = self.env.ref('account.email_template_edi_invoice',
    #                                   raise_if_not_found=False)
    #
    #     for picking in self:
    #         # FIXME: If there is multiple sales order for single transfer that will break the logic
    #         sale_ids = picking.move_ids.mapped("sale_line_id").mapped("order_id")
    #         if not sale_ids:
    #             continue
    #
    #         move_ids = picking.account_move_ids
    #         if not move_ids:
    #             continue
    #
    #
    #         sale_id = sale_ids[0]
    #         if not sale_id.payment_term_id.auto_email_invoice:
    #             continue
    #
    #
    #         for move in move_ids.filtered(lambda m: not m.is_emailed):
    #             lang = False
    #             if email_template:
    #                 lang = email_template._render_lang(move_ids.ids).get(move.id, False)
    #                 # lang = email_template._render_lang(move_ids.ids)[move.id]
    #
    #             emails = set(sale.partner_invoice_id.email for sale in sale_ids if sale.partner_invoice_id.email)
    #             if emails:
    #                 email_template.write({'email_to': ','.join(emails)})
    #             else:
    #                 raise ValueError(_("No valid email addresses found for the sale order(s)."))
    #             # email_template.write({'email_to': ','.join(emails)})
    #
    #             ctx = dict(
    #                 mark_invoice_as_sent=True,
    #                 active_ids=move_ids.ids,
    #                 custom_layout="mail.mail_notification_paynow",
    #                 model_description=move.with_context(lang=lang).type_name,
    #                 force_email=True,
    #                 default_res_model='account.move',
    #                 default_use_template=bool(email_template))
    #
    #             values = {
    #                 'model': 'account.move',
    #                 'res_id': move.id,
    #                 'is_email':True,
    #                 'template_id': email_template and email_template.id or False,
    #                 'composition_mode': 'comment',
    #             }
    #
    #             wizard = self.env['account.invoice.send'].with_context(ctx).create(values)
    #             wizard._compute_composition_mode()
    #             wizard.send_and_print_action()
    #             email_template.write({'email_to': ""})
    #             move.write({'is_emailed': True})
    #
    #     return res

    def _action_done(self):
        res = super(Picking, self)._action_done()
        email_template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)

        for picking in self:
            sale_ids = picking.move_ids.mapped("sale_line_id").mapped("order_id")
            if not sale_ids:
                continue

            move_ids = picking.account_move_ids
            if not move_ids:
                continue

            for sale_id in sale_ids:
                if not sale_id.payment_term_id.auto_email_invoice:
                    continue

                emails = {sale.partner_invoice_id.email for sale in sale_ids if sale.partner_invoice_id.email}
                if not emails:
                    raise ValueError(_("No valid email addresses found for the sale order(s)."))

                for move in move_ids.filtered(lambda m: not m.is_emailed):
                    if email_template:
                        email_template.with_context(
                            lang=move.partner_id.lang,
                            email_to=','.join(emails),
                            mark_invoice_as_sent=True
                        ).send_mail(move.id, force_send=True)
                    move.write({'is_emailed': True})
        return res
