from odoo import fields, models,api

class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    reference_number = fields.Char(string="Reference Number", readonly=True)

    def _select(self):
        select_query = super()._select()
        select_query += ", move.reference_number as reference_number"
        return select_query

    def _group_by(self):
        group_by_query = super()._group_by()
        group_by_query += ", move.reference_number"
        return group_by_query