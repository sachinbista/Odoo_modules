# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    def unlink(self):
        '''
            Checking whether the account
            is set on warehouse or not
        '''
        if self.ids:
            warehouse = self.env['stock.warehouse'].search([
                '|', '|', '|',
                ('account_receivable_id', 'in', self.ids),
                ('account_payable_id', 'in', self.ids),
                ('account_income_id', 'in', self.ids),
                ('account_expense_id', 'in', self.ids)], limit=1)
            if warehouse:
                raise UserError(_(
                    '''you cannot remove/deactivate an account \
which is configured on warehouse in Odoo.'''))
        return super(AccountAccount, self).unlink()
