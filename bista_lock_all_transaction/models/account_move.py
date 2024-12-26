# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        if self.partner_id and self.partner_id.lock_all_transaction:
            raise ValidationError(_("The customer has locked all transactions. You cannot validate this invoice."))
        return super().action_post()
