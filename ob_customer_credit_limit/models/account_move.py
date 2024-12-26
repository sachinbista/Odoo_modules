# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'


    # def _compute_amount(self):
    #     ret = super(AccountMove, self)._compute_amount()
    #     for move in self:
    #         if move.payment_state in ['in_payment', 'paid'] and move.partner_id.credit_check:
    #             print(">>>>>>>_compute_amount>>")
    #             move.partner_id.recalculate_credit_limit = True
    #     return ret

    @api.depends('amount_residual', 'move_type', 'state', 'company_id')
    def _compute_payment_state(self):
        res = super()._compute_payment_state()
        for move in self:
            if move.payment_state in ['in_payment', 'paid'] and move.partner_id.credit_check:
                move.partner_id.recalculate_credit_limit = True
        return res



