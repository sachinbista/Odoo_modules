# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'




    def action_post(self):
        if self.partner_id and self.partner_id.lock_all_transaction:
            raise ValidationError(_("All Transactions are locked."))
        return super().action_post()

    @api.depends('amount_residual', 'move_type', 'state', 'company_id')
    def _compute_payment_state(self):
        res = super()._compute_payment_state()
        for move in self:
            if move.payment_state in ['in_payment', 'paid'] and move.partner_id.credit_check:
                # move.partner_id.recalculate_credit_limit = True
                move.partner_id._compute_credit_threshold()
        return res



