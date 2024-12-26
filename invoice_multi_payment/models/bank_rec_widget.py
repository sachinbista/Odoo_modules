# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, fields, models, _

class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    def _action_add_new_batch_payments(self, batch_payments):
        self.ensure_one()
        amls = self.env['account.move.line']
        amls_domain = self.st_line_id._get_default_amls_matching_domain()
        mounted_payments = set(self.line_ids.filtered(lambda x: x.flag == 'new_aml').source_aml_id.payment_id)
        for batch in batch_payments:
            for payment in batch.payment_ids:
                if payment not in mounted_payments:
                    liquidity_lines, _counterpart_lines, _writeoff_lines, _discount_lines, _sale_tax_line = payment._seek_for_lines()
                    amls |= liquidity_lines.filtered_domain(amls_domain)
        self._action_add_new_amls(amls, allow_partial=False)