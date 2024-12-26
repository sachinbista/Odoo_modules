from odoo import models, api, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    aquirers_to_show = fields.Selection([
        ('all_minus_credit_account', 'Block credit account'),
        ('wire_and_account_only', 'Wire transfer and Credit account only')],
        string='Payments options', default='all_minus_credit_account')

