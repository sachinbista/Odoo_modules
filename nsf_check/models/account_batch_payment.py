from odoo import models, fields, api, _


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    @api.depends('payment_ids.move_id.is_move_sent', 'payment_ids.is_matched', 'payment_ids.is_check_bounce')
    def _compute_state(self):
        for batch in self:
            if batch.payment_ids and all((pay.is_matched or pay.is_check_bounce) and pay.is_move_sent for pay in batch.payment_ids):
                batch.state = 'reconciled'
            elif batch.payment_ids and all(pay.is_move_sent for pay in batch.payment_ids):
                batch.state = 'sent'
            else:
                batch.state = 'draft'