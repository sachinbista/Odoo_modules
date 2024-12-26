# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models
from odoo.tools.misc import get_lang


class Picking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        res = super(Picking, self)._action_done()
        sale_order_id = self.sale_id or self.intercom_sale_order_id
        if sale_order_id and not sale_order_id.stock_transfer_id:
            if self.move_ids \
                    and self.picking_type_id.code == 'outgoing' or self.picking_type_id.code=='incoming' \
                    and self.company_id.auto_create_invoice:
                move_ids = self.move_ids.filtered(
                    lambda x:
                    x.sale_line_id and x.state == 'done' and
                    x.product_id.invoice_policy == 'delivery')
                sale_order = move_ids.mapped(
                    'sale_line_id').mapped('order_id')
                if sale_order:
                    #moves = sale_order.sudo()._create_invoices(final=True)
                    account_moves = sale_order.with_env(sale_order.env(
                        user=1))._create_invoices(final=True)
                    sale_line_ids = sale_order.order_line.filtered(lambda x: x.product_id.type != 'service')
                    if all(line.product_uom_qty == line.qty_delivered for line in sale_line_ids):
                        sale_order.state = 'done'
                    if self.company_id.auto_send_mail_invoice:
                        template = self.env.ref(
                            'account.email_template_edi_invoice', raise_if_not_found=False)
                        lang = get_lang(self.env)
                        if template and template.lang:
                            lang = template._render_template(
                                template.lang, 'account.move', account_moves.id)
                        else:
                            lang = lang.code
                        ctx = dict(
                            default_model='account.move',
                            mark_invoice_as_sent=True,
                            custom_layout="mail.mail_notification_paynow",
                            model_description=account_moves.with_context(
                                lang=lang).type_name,
                            force_email=True
                        )
                        template.with_context(ctx).send_mail(
                            account_moves.id, force_send=True)

                    if self.company_id.auto_validate_invoice:
                        # moves.with_env(moves.env(user=1)).action_post()
                        account_moves.with_env(account_moves.env(user=1)).with_context(
                            {'picking_id': self}).action_post()
            '''
            After outgoing shipment return then Automatically created credit notes
            '''
            # if self.move_ids and self.picking_type_id.code != 'internal':
            #     move_ids = self.move_ids.filtered(
            #         lambda x:
            #         x.sale_line_id and x.state == 'done' and
            #         x.product_id.invoice_policy == 'delivery'
            #         and x.to_refund)
            #     sale_order = move_ids.mapped(
            #         'sale_line_id').mapped('order_id')
            #     if sale_order:
            #         # sale_order.sudo()._create_invoices(final=True)
            #         sale_order.with_env(sale_order.env(
            #             user=1))._create_invoices(final=True)
        return res
