from odoo import models, api,fields,_
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_send_and_print_invoice(self):
        self.ensure_one()
        if not self.partner_id.invoice_send:
            raise UserError(_("Cannot send invoice: Partner %s is not authorized to receive invoices. Please check the 'Can Send Invoice' setting on the partner form.") % self.partner_id.name)
        return super(AccountMove, self).action_send_and_print_invoice()

    def action_invoice_sent(self):
        self.ensure_one()
        if not self.partner_id.invoice_send:
            raise UserError(_("Cannot send invoice: Partner %s is not authorized to receive invoices. Please check the 'Can Send Invoice' setting on the partner form.") % self.partner_id.name)
        return super(AccountMove, self).action_invoice_sent()

    def action_post(self):
        for rec in self:
            shiping_line = rec.invoice_line_ids.filtered(lambda line: line.is_delivery)
            if rec.partner_id.is_require_shipping and not shiping_line:
                raise UserError(_("Cannot validate invoice: requires shipping."))
        return super(AccountMove, self).action_post()
