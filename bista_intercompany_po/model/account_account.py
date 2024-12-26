from odoo import models, api,fields,_


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model
    def _get_most_frequent_account_for_partner(self, company_id, partner_id, move_type=None):
        if partner_id and move_type == 'in_invoice':
            partner = self.env['res.partner'].sudo().browse(partner_id)
            return partner.gl_account_id.id
        return super()._get_most_frequent_account_for_partner(company_id, partner_id, move_type)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    internal_order_ref = fields.Char(related='move_id.internal_order_ref',
                                     string="Order Reference/Owner's reference",
                                     store=True, readonly=False)

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMoveLine, self).default_get(fields_list)
        if self._context.get('move_id'):
            move = self.env['account.move'].browse(self._context['move_id'])
            if move.partner_id:
                if move.move_type in ['in_invoice', 'in_refund']:
                    res['account_id'] = move.partner_id.gl_account_id.id

        return res

    @api.onchange('partner_id', 'move_id')
    def _onchange_partner_account(self):
        for line in self:
            if line.partner_id and line.move_id.move_type:
                if line.move_id.move_type in ['in_invoice', 'in_refund']:
                    line.account_id = line.partner_id.gl_account_id


class AccountMove(models.Model):
    _inherit = 'account.move'

    internal_order_ref = fields.Char(string="Order Reference/Owner's reference")
    reference_number = fields.Char(string="Reference Number")

    def action_post(self):
        res = super().action_post()
        if (self.move_type == 'out_invoice' and self.name == self.payment_reference and
                self.reference_number):
            self.payment_reference = self.reference_number
        return res


    @api.onchange('partner_id')
    def _onchange_partner_update_lines(self):
        for move in self:
            for line in move.invoice_line_ids:
                if not line.partner_id or line.partner_id != move.partner_id:
                    line.partner_id = move.partner_id

                if move.move_type in ['in_invoice','in_refund',]:
                    line.account_id = move.partner_id.gl_account_id


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    internal_order_ref = fields.Char(string="Order Reference/Owner's reference")


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    internal_order_ref = fields.Char(string="Order Reference/Owner's reference")

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        vals = super()._get_wizard_values_from_batch(batch_result)

        if batch_result and batch_result.get('lines'):
            move = batch_result['lines'][0].move_id
            if move:
                vals['internal_order_ref'] = move.internal_order_ref
        return vals

    def _create_payment_vals_from_wizard(self, batch_result):  # Added batch_result parameter
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['internal_order_ref'] = self.internal_order_ref
        return payment_vals
