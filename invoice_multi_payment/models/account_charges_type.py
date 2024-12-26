from odoo import models, fields, api, _


class AccountChargesType(models.Model):
    _name = 'account.charges.type'
    _description = "Account Charges Type"

    name = fields.Char('Name')
    account_id = fields.Many2one('account.account')

    _sql_constraints = [(
            "account_charges_type_unique",
            "UNIQUE(name, account_id)",
            "The account must be unique per charges type !",
        )]
