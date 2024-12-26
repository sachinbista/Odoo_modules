# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _action_send_mail(self, auto_commit=False):
        res = super(MailComposeMessage, self)._action_send_mail(auto_commit=auto_commit)
        if self.model == 'sale.order' and 'proforma' in self._context:
            active_ids = self._context.get('active_ids')
            sale_id = self.env['sale.order'].browse(active_ids)
            if sale_id.state not in ('sale','cancel','done'):
                sale_id.update({
                    'state': 'proforma'
                    })
        return res