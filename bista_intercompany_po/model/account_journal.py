from odoo import models, api,fields,_


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_vendor_journal = fields.Boolean(string='Is Inter-Company Vendor Pyament',copy=False)
    is_customer_journal = fields.Boolean(string='Is Inter-company Customer Payment',copy=False)
