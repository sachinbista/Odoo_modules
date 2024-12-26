# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from datetime import datetime
from odoo import models
from odoo.tools.misc import get_lang


class Picking(models.Model):
    _inherit = "stock.picking"

    def action_create_bill(self, purchase_id):
        vals = self.env['account.move'].with_context(default_type='in_invoice').default_get(
                    ['journal_id', 'date', 'invoice_date', 'invoice_payment_term_id'])
        addr = purchase_id.partner_id.address_get(['delivery'])
        bill_date = datetime.today()
        if self.picking_type_id.code == 'incoming':
            vals.update({'move_type': 'in_invoice'})
        elif self.picking_type_id.code == 'outgoing':
            vals.update({'move_type': 'in_refund'})
        vals.update({
            'partner_shipping_id': addr and addr.get('delivery'),
            'invoice_origin': purchase_id.name,
            'ref': purchase_id.partner_ref or purchase_id.origin or purchase_id.name,
            'purchase_id': purchase_id.id,
            'fiscal_position_id': purchase_id.fiscal_position_id.id,
            'currency_id': purchase_id.currency_id.id,
            'invoice_payment_term_id': purchase_id.payment_term_id.id,
            'partner_id': purchase_id.partner_id.id,
            'date': bill_date,
            'invoice_date': bill_date
        })
        move_id = self.env['account.move'].with_env(self.env(user=1)).create(vals)
        move_id._onchange_partner_id()
        # Copy purchase lines.
        po_lines = purchase_id.order_line - move_id.line_ids.mapped('purchase_line_id')
        new_lines = self.env['account.move.line']
        if self.picking_type_id.code == 'incoming':
            for line in po_lines.filtered(lambda l: not l.display_type and l.qty_received > 0 and l.qty_received - l.qty_invoiced != 0):
                new_line = new_lines.new(line._prepare_account_move_line(move_id))
                new_line.date = bill_date
                new_line.date_maturity = bill_date
                new_lines += new_line
        if self.picking_type_id.code == 'outgoing':
            for line in po_lines.filtered(lambda l: not l.display_type and l.qty_received - l.qty_invoiced != 0):
                new_line = new_lines.new(line._prepare_account_move_line(move_id))
                new_line.date = bill_date
                new_line.date_maturity = bill_date
                new_lines += new_line
        move_id.update({'invoice_line_ids': new_lines, 'purchase_id': False, 'date': bill_date, 'invoice_date': bill_date})
        if self.company_id.auto_send_mail_bill:
            template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
            lang = get_lang(self.env)
            if template and template.lang:
                lang = template._render_template(template.lang, 'account.move', move_id.ids)
            else:
                lang = lang.code
            ctx = dict(
                default_model='account.move',
                mark_invoice_as_sent=True,
                custom_layout="mail.mail_notification_paynow",
                model_description=move_id.with_context(lang=lang).type_name,
                force_email=True
            )
            template.with_context(ctx).send_mail(move_id.id, force_send=True)
        if self.company_id.auto_validate_bill:
            move_id.with_env(move_id.env(user=1)).action_post()
        return move_id

    def _action_done(self):
        res = super(Picking, self)._action_done()
        if (not self.stock_transfer_id and self.move_ids and
                self.picking_type_id.code == 'incoming' or self.picking_type_id.code == 'outgoing' and
                self.company_id.auto_create_bill):
                move_lines = self.move_ids.filtered(
                    lambda x: x.purchase_line_id and x.state == 'done')
                purchase_id = move_lines.mapped('purchase_line_id').mapped('order_id')
                if purchase_id:
                    self.with_env(self.env(user=1)).action_create_bill(purchase_id)
        return res
