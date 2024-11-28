from odoo import models, api, fields, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    is_intercompany_po = fields.Boolean(string='Is Intercompany PO', default=False)
