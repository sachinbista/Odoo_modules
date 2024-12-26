from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    description = fields.Char(string='Description')
    type = fields.Char(string='Type')
    basis_date_code = fields.Char(string='Basis Date Code')
    discount_percentage = fields.Char(string='Discount Percentage')
    discount_date = fields.Char(string='Discount Date')
    discount_due_days = fields.Char(string='Discount Due Days')
    net_due_date = fields.Char(string='Net Due Date')
    net_due_days = fields.Char(string='Net Due Days')
