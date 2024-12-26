# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        """"Override to process suitable_journal_ids domain."""
        res = super(AccountMove, self)._compute_suitable_journal_ids()
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            if journal_type == 'general' and m.move_type == 'entry':
                domain = [('company_id', '=', company_id), ('type', '=', journal_type), ('allow_manual_entry', '=', True)]
            else:
                domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)
        return res

    def _search_default_journal(self):
        if self.payment_id and self.payment_id.journal_id:
            return self.payment_id.journal_id
        if self.statement_line_id and self.statement_line_id.journal_id:
            return self.statement_line_id.journal_id
        if self.statement_line_ids.statement_id.journal_id:
            return self.statement_line_ids.statement_id.journal_id[:1]

        journal_types = self._get_valid_journal_types()
        company_id = (self.company_id or self.env.company).id

        if journal_types[0] == 'general' and self.move_type == 'entry':
            domain = [('company_id', '=', company_id), ('type', 'in', journal_types), ('allow_manual_entry', '=', True)]
        else:
            domain = [('company_id', '=', company_id), ('type', 'in', journal_types)]

        journal = None
        # the currency is not a hard dependence, it triggers via manual add_to_compute
        # avoid computing the currency before all it's dependences are set (like the journal...)
        if self.env.cache.contains(self, self._fields['currency_id']):
            currency_id = self.currency_id.id or self._context.get('default_currency_id')
            if currency_id and currency_id != self.company_id.currency_id.id:
                currency_domain = domain + [('currency_id', '=', currency_id)]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            company = self.env['res.company'].browse(company_id)

            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        return journal

    def action_post(self):
        """
        Custom action to be executed when posting a vendor bill.
        """
        # Call the parent method to retain the original functionality
        result = super(AccountMove, self).action_post()
        # Additional custom code
        for move in self:
            if not move.ref and move.move_type == 'in_invoice':
                raise UserError(_('The bill reference is required to validate this document.'))
        return result



class AccountJournal(models.Model):
    _inherit = 'account.journal'

    allow_manual_entry = fields.Boolean(string="Allow manual Entry")

