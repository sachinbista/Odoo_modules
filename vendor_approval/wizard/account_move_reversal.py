# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    @api.model
    def default_get(self, fields):
        values = super(AccountMoveReversal, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get(
            'active_model') == 'account.move' else self.env['account.move']

        if 'active_model' in self._context and self._context.get('active_model') == 'account.move' and 'default_move_type' in self._context and self._context.get('default_move_type') in ('in_invoice', 'in_refund', 'in_receipt'):
            for move_id in move_ids:
                if move_id.approval_status != 'payment_to_pay' and move_id.move_type in ('in_invoice', 'in_receipt'):
                    raise UserError(_("You can not reverse before approval."))

        return values