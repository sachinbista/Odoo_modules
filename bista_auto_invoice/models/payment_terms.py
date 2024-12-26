from odoo import models, api, fields


class PaymentTerms(models.Model):
    _inherit = 'account.payment.term'

    auto_invoice = fields.Boolean()

#
# class SaleOrderLine(models.Model):
#     _inherit = 'sale.order.line'
#
#     def _prepare_invoice_line(self, **optional_values):
#         """
#             If the sale order line isn't linked to a sale order which already have a default analytic account,
#             this method allows to retrieve the analytic account which is linked to project or task directly linked
#             to this sale order line, or the analytic account of the project which uses this sale order line, if it exists.
#         """
#         return super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)