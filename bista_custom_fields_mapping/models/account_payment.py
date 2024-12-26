# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools.misc import formatLang, format_date


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_blank_check = fields.Boolean(string='Is Blank Check')

    @api.model
    def default_get(self, fields):
        ctx = dict(self._context or {})
        result = super(AccountPayment, self).default_get(fields)
        if ctx.get('default_payment_type') == 'outbound' and ctx.get('default_partner_type') == 'supplier':
            journal_id = self.env['account.journal'].search([('is_default_bank_account', '=', True)], limit=1)
            if journal_id:
                result['journal_id'] = journal_id.id
        return result

    def print_checks(self):
        check_type = self.env['ir.config_parameter'].sudo().get_param('bv_esbi_account_extended.check_selection')
        if check_type == 'pre_printed_check':
            res = super(AccountPayment, self).print_checks()
            self.is_blank_check = False
            return res
        elif check_type == 'blank_check':
            return self.print_blank_checks()

    def print_blank_checks(self):
        """ Check that the recordset is valid, set the payments state to sent and call print_checks() """
        # Since this method can be called via a client_action_multi, we need to make sure the received records are what we expect
        self = self.filtered(lambda r: r.payment_method_id.code == 'check_printing' and r.state != 'reconciled')

        if len(self) == 0:
            raise UserError(_("Payments to print as a checks must have 'Check' selected as payment method and "
                              "not have already been reconciled"))
        if any(payment.journal_id != self[0].journal_id for payment in self):
            raise UserError(_("In order to print multiple checks at once, they must belong to the same bank journal."))
        self.is_blank_check = True
        if not self[0].journal_id.check_manual_sequencing:
            # The wizard asks for the number printed on the first pre-printed check
            # so payments are attributed the number of the check the'll be printed on.
            self.env.cr.execute("""
                  SELECT payment.id
                    FROM account_payment payment
                    JOIN account_move move ON movE.id = payment.move_id
                   WHERE journal_id = %(journal_id)s
                   AND check_number IS NOT NULL
                ORDER BY check_number::INTEGER DESC
                   LIMIT 1
            """, {
                'journal_id': self.journal_id.id,
            })
            last_printed_check = self.browse(self.env.cr.fetchone())
            number_len = len(last_printed_check.check_number or "")
            next_check_number = '%0{}d'.format(number_len) % (int(last_printed_check.check_number) + 1)
            return {
                'name': _('Print Blank Checks'),
                'type': 'ir.actions.act_window',
                'res_model': 'print.prenumbered.checks',
                'view_mode': 'form',
                'view_id': self.env.ref('bv_esbi_account_extended.print_blank_checks_view').id,
                'target': 'new',
                'context': {
                    'payment_ids': self.ids,
                    'default_next_check_number': next_check_number,
                }
            }
        else:
            self.filtered(lambda r: r.state == 'draft').action_post()
            return self.do_print_checks()

    def _check_build_page_info(self, i, p):
        res = super(AccountPayment, self)._check_build_page_info(i, p)

        if self.journal_id:
            res.update({
                           'account_number': self.journal_id.bank_account_id.acc_number if self.journal_id.bank_account_id.acc_number else False,
                           'aba_routing': self.journal_id.bank_account_id.aba_routing,
                           'is_blank_check': self.is_blank_check})

        return res

    is_duplicate = fields.Boolean(string='Is Duplicate')

    def reprint_checks(self):
        return self.with_context(duplicate=True).do_print_checks()

    def do_print_checks(self):
        if self._context.get('duplicate', False):
            self.is_duplicate = True
        else:
            self.is_duplicate = False
        res = super(AccountPayment, self).do_print_checks()
        return res

    def _check_build_page_info(self, i, p):
        res = super(AccountPayment, self)._check_build_page_info(i, p)
        res.update({'is_duplicate': self.is_duplicate})
        return res