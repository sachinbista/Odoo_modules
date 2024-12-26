from odoo import models, api, fields


class PaymentTerms(models.Model):
    _inherit = 'account.payment.term'

    auto_email_invoice = fields.Boolean(
        help="Auto send invoice when picking is marked as done.")
