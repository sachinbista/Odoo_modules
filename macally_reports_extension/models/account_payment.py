##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _check_build_page_info(self, i, p):
        page = super(AccountPayment, self)._check_build_page_info(i, p)
        page.update({
            'company_id': self.company_id,
            'company_name': self.company_id.name,
            'vendor_ref': self.partner_id.ref
        })
        if 'amount' in page:
            page.update({
                'amount': ('*' + page.get('amount')).rjust(13, '*') or '',
            })
        if 'stub_lines' in page:
            stub_lines = page.get('stub_lines')
            for each_rec in stub_lines:
                if each_rec.get('amount_residual') == "-":
                    each_rec.update({'amount_residual': '$\xa00.00'})
        return page

    def _check_fill_line(self, amount_str):
        return amount_str and (amount_str + ' ').ljust(100, '*') or ''


