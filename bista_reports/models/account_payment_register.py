# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    want_to_send_email = fields.Boolean(string="Want To Send Email ?")

    def action_create_payments(self):
        if self.want_to_send_email:
            return super(AccountPaymentRegister, self.with_context(
                {'want_to_send_email': True, 'dont_redirect_to_payments': True})).action_create_payments()
        return super(AccountPaymentRegister, self).action_create_payments()
