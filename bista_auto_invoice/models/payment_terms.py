from odoo import models, api, fields


class PaymentTerms(models.Model):
    _inherit = 'account.payment.term'

    auto_invoice = fields.Boolean(
        help="Auto create invoice when sales order is confirmed and product is "
             "delivered based on the product invoicing policy.")
    force_all_products = fields.Boolean(
        help='If checked, odoo will invoice all products '
             'including those which has not been delivered yet.')
    auto_payment = fields.Boolean(string="Auto Payment")

    @api.onchange('auto_payment')
    def _onchange_auto_payment(self):
        for rec in self:
            if rec.auto_payment:
                rec.auto_invoice = True
