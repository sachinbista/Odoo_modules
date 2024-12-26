# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, api, fields, _


class InvoiceDateWizard(models.TransientModel):
    _name = "invoice.date.wizard"
    _description = "invoice.date.wizard"

    name = fields.Char('Warning')
    move_id = fields.Many2one('account.move', string='Move')

    def action_process(self):
        self.move_id.with_context(is_invoice_date=True).action_post()
