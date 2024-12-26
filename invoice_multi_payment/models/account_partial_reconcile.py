from odoo import models, fields


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    payment_id = fields.Many2one(
        'account.payment',
        string="Payment",
        copy=False,
        help="Payment id of the payment from which this allocation is done.")
