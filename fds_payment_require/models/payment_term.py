from odoo import models, api, fields


class PaymentTerms(models.Model):
    _inherit = 'account.payment.term'

    payment_require = fields.Boolean(string="Payment Require")
