# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_default_bank_account = fields.Boolean(string="Is Default Bank Account", copy=False)

    @api.constrains('is_default_bank_account')
    def default_bank_account_validation(self):
        if (self.search_count([('is_default_bank_account', '=', True), ('id', 'not in', [self.id])])) >= 1:
            journal_id = self.search([('is_default_bank_account', '=', True), ('id', 'not in', [self.id])])
            raise ValidationError(
                _('Sorry,You can not set the Default Bank Account. Because it already configure into the another journal : %s' % journal_id.name))

class AccountMove(models.Model):
    _inherit = 'account.move'

    ownership = fields.Selection(string='Ownership', selection=[('owned', 'Owned'), ('memo', 'Memo')], default='owned')