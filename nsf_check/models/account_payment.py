# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_check_bounce = fields.Boolean('Check Bounce', copy=False)
    bounce_move_id = fields.Many2one('account.move', string="Bounce Move", copy=False)
    show_bounce_button = fields.Boolean(compute='_compute_show_bounce_button')


    def _compute_show_bounce_button(self):
        for rec in self:
            if rec.payment_type == 'inbound' and rec.partner_type == 'customer' and rec.payment_method_id.name == 'Check':
                rec.show_bounce_button = True
            else:
                rec.show_bounce_button = False

    def action_view_bounce_entry(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        form_view = [(self.env.ref('account.view_move_form').id, 'form')]
        if 'views' in action:
            action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
        else:
            action['views'] = form_view
        action['res_id'] = self.bounce_move_id.id
        return action

    def check_bounce(self):
        view_id = self.env.ref('nsf_check.view_check_bounce_form')
        return {
            'name': _("Check Bounce"),
            'view_mode': 'form',
            'view_id': view_id.id,
            'res_model': 'check.bounce.wizard',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': {'default_invoice_ids': self.reconciled_invoice_ids.ids,
                        'default_account_payment_id': self.id}
        }

    def action_draft(self):
        res = super(AccountPayment, self).action_draft()
        if self.is_check_bounce:
            self.is_check_bounce = False
        return res

    def action_cancel(self):
        res = super(AccountPayment, self).action_cancel()
        if self.is_check_bounce:
            self.is_check_bounce = False
        return res

class account_move(models.Model):
    _inherit = "account.move"

    bounce_id = fields.Many2one('account.payment', string="Bounce",copy=False)
    

