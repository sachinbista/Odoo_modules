# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class PrintPreNumberedChecks(models.TransientModel):
    _inherit = 'print.prenumbered.checks'

    def print_checks(self):
        '''Update messages in footer...'''
        context = dict(self._context)
        if context is None:
            context = {}
        result = super(PrintPreNumberedChecks, self).print_checks()
        active_ids = context.get('active_ids') or context.get('payment_ids')
        payment_ids = self.env['account.payment'].browse(active_ids)
        for payments in payment_ids:
            message = ('''
            <ul class="o_mail_thread_message_tracking">
                <li>Check Updated Date: %s</li>
                <li>Check Number: %s (Generated)</li>
                <li>State: %s</li>
            </ul>''') % (
                datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
                payments.check_number, payments.state.title())
            payments.message_post(body=message)
            payments.write({'is_hide_check': False})
        return result
        # return {'type': 'ir.actions.act_window_close'}
