# -*- coding: utf-8 -*-
from odoo import models, fields


class CreditLimitWizard(models.TransientModel):
    _name = "credit.limit.wizard"
    _description = "credit limit Wizard"

    name = fields.Text(string="Message", readonly=True)

    def action_continue(self):
        active_id = self._context.get("active_id")
        if active_id:
            invoice = self.env['account.move'].browse(active_id)
            invoice.state = 'credit_review'
