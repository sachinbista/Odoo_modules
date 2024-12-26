# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveReversal(models.TransientModel):
    """
    Account move reversal wizard, it cancel an account move by reversing it.
    """

    _inherit = 'account.move.reversal'
    _description = 'Account move reversal'

    action_type = fields.Selection([
        ('void_check', 'Void Check'),
        ('void_payment', 'Void Check & Payment')], string="Action",
        default='void_check')

    @api.model
    def default_get(self, fields):
        defaults = super(AccountMoveReversal,
                         self).default_get(fields)
        payment_id = self.env['account.payment'].browse(
            self._context.get('active_ids')[0])

        if self._context.get('active_model') == 'account.payment':
            defaults.update({
                'move_ids': [(4, payment_id.move_id.id)]
            })
        return defaults

    def reverse_moves(self):
        res = super(AccountMoveReversal, self).reverse_moves()
        payment_check_void_obj = self.env['payment.check.void']
        pay_obj = self.env['account.payment']
        payment_check_history_obj = self.env['payment.check.history']
        move_line_obj = self.env['account.move.line']
        today_date = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
        payment = self._context.get('active_ids')
        #Reverse Reconciliation: Initialization
        reversal_debt_line_ids = False

        for pay in payment:
            if self._context.get('is_void_button') and pay and self._context.get('active_model') == 'account.payment':
                payment_id = pay_obj.browse(pay)

                if payment_id.state in ('draft', 'void'):
                    raise ValidationError(
                        'You can reverse payments which is the status of\
                        payment posted or sent.')

                payment_check_void_obj.create(
                    {'bill_ref': payment_id.ref,
                     'create_date': today_date,
                     'check_number': payment_id.check_number, 'state': 'void',
                     'payment_id': payment_id.id})
                payment_id.write({'is_hide_check': True, 'is_void': True})
                domain = [('payment_id', '=', payment_id.id),
                          ('partner_id', '=', payment_id.partner_id.id),
                          ('journal_id', '=', payment_id.journal_id.id)]
                payment_check_history_ids = (
                    payment_check_history_obj.
                    search(domain, order='id DESC', limit=1))
                payment_check_history_ids.write({'state': 'void'})
                payment_id.is_move_sent = False

                today_date = datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)
                message = (
                    '''<table border="1" style="text-align: center; width:600px;">
                            <tr>
                                <td>Bill Number</td>
                                <td>Void Check Number</td>
                                <td>Check Voided Date</td>
                                <td>Status</td>
                            </tr>
                            <tr>
                                <td>%s</td>
                                <td>%s</td>
                                <td>%s</td>
                                <td>%s</td>
                            </tr>
                          </table>
                        ''') % (
                payment_id.ref or '', payment_id.check_number or '',
                today_date or '',
                payment_id.state.title() or '')
                payment_id.message_post(body=message)

            if res.get('res_id'):
                move_id = self.env['account.move'].browse(res.get('res_id'))
                if move_id.state == 'draft' and self._context.get('active_model') == 'account.payment':
                    move_id._post()

                #Reverse Reconciliation(start): Filtered Reversal Debt Line IDs.
                reversal_debt_line_ids = move_id.line_ids.\
                    filtered(lambda x: x.debit > 0 and\
                        x.account_id.account_type == 'asset_current')
                #Reverse Reconciliation(End)

                self._cr.execute('''
                    SELECT aml.full_reconcile_id FROM account_payment AS ap
                    INNER JOIN account_move_line AS aml
                        ON aml.payment_id=ap.id
                        AND ap.id = %s
                        AND full_reconcile_id IS NOT NULL
                    INNER JOIN account_move AS am
                        ON aml.move_id = am.id
                ''' % (pay))
                full_reconcile_ids = self._cr.fetchone()

                query = '''SELECT id FROM account_move_line
                    WHERE payment_id = %s''' % (pay)
                aml_ids = []
                if full_reconcile_ids:
                    full_reconcile_id = full_reconcile_ids[0]
                    query += " AND full_reconcile_id = %s" % (
                        full_reconcile_id)

                self._cr.execute(query)
                aml_ids = [aml[0] for aml in self._cr.fetchall()]

                if aml_ids:
                    # Unrecncile aml.
                    aml_rec = move_line_obj.browse(aml_ids)
                    aml_rec.remove_move_reconcile()
                    _logger.info("Unreconcile Journal items: %s" % (aml_rec))

                    rec_move_line_ids = payment_credit_line_ids = self.env['account.move.line']

                    for line in payment_id.move_id.line_ids:
                        if line.account_id.account_type in ('asset_receivable', 'liability_payable'):
                            if line not in rec_move_line_ids:
                                rec_move_line_ids += line
                        #Reverse Reconciliation(Start): Current Assets type move lines from the main payment.
                        if line.credit > 0 and line.account_id.account_type == 'asset_current':
                            if line not in payment_credit_line_ids:
                                payment_credit_line_ids |= line
                        #Reverse Reconciliation(End).

                    # This line added for Refund and Bill Unreconcile.
                    # If Refund use with Bill in Payment which you are void
                    # check and Reverse.
                    # Issue generated: Refund invoice not going to Open state
                    # after click Void Check & Payment.
                    # This same issue is in Runbot system Refund + Bill
                    # payment JE's select and Unreconcile.
                    for inv in payment_id.reconciled_bill_ids.filtered(
                        lambda p: p.type in ['in_refund', 'out_refund']):
                        inv.line_ids.remove_move_reconcile()

                    for nmove in move_id:
                        for nmv_line in nmove.line_ids:
                            if nmv_line.account_id.account_type in ('asset_receivable', 'liability_payable'):
                                if nmv_line not in rec_move_line_ids:
                                    rec_move_line_ids += nmv_line
                    if rec_move_line_ids:
                        rec_move_line_ids.reconcile()
                    #Reverse Reconciliation: Reversal Debt Line Ids and Payment Credit Line Ids Reconciliation.
                    if reversal_debt_line_ids and payment_credit_line_ids:
                        (reversal_debt_line_ids+payment_credit_line_ids).reconcile()
                    #Reverse Reconciliation(End).

        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False,
                        submenu=False):
        res = super(AccountMoveReversal, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        context = self._context
        pay_obj = self.env['account.payment']
        if context.get('active_model') == 'account.payment' and\
            context.get('active_ids'):
            pay_ids = self._context.get('active_ids', False)
            for pay in pay_obj.browse(pay_ids):
                if pay.state in ('draft', 'cancel'):
                    raise ValidationError('''
                    State of payment is not posted or sent. Please select
                    posted or sent payments only to reverse payment''')
        return res
