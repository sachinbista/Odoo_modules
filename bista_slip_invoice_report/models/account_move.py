# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    def check_company(self):
        if self.company_id.country_id.code != 'AU':
            return False
        return True

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        # Check for reports only available for invoices.
        # if self._get_report(report_ref).report_name == 'bista_slip_invoice_report.report_proforma_invoice_document':
        #     invoices = self.env['account.move'].browse(res_ids)
        #     if invoices.company_id.country_id.code != 'AU':
        #         raise UserError(_("Only Australia Company invoices could be printed."))

        return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
