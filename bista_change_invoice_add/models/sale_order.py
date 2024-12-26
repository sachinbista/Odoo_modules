from odoo import fields, models, api, _
import logging
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def change_invoice_address(self):
        for order in self:
            try:
                if order.partner_invoice_id and order.partner_invoice_id.type == 'delivery':
                    order.partner_invoice_id = order.partner_id
                if order.invoice_ids:
                    for invoice in order.invoice_ids:
                        invoice.partner_id = order.partner_invoice_id
            except Exception as e:
                _logger.error(f"Failed to change invoice address for order {order.id}: {e}")
                raise UserError(_("Failed to change invoice address. Please try again."))

