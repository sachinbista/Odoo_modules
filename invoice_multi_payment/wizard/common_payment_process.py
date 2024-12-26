from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CommonPaymentProcess(models.TransientModel):
    _name = 'common.payment.process'


    payment_id = fields.Many2one('account.payment', string="Payment")
    current_payment_amount = fields.Float(string="Current Payment Amount", digits='Product Price')
    total_amount = fields.Float(string="Total Payment Amount", digits='Product Price')
    remaining_amount = fields.Float(string="Remaining Amount", digits='Product Price')
    discount_amount = fields.Float(string="Discount Amount", digits='Product Price')
    sale_tax = fields.Float(string="Sale Tax", digits='Product Price')
    writeoff_amount = fields.Float(string="Writeoff Amount", digits='Product Price')

    sale_tax_account_id = fields.Many2one('account.account', string="Sale Tax Account")

    def default_get(self, fields_list):
        res = super(CommonPaymentProcess, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        payment_id = self.env['account.payment'].browse(active_id)
        if payment_id.is_hide_allocation:
            raise UserError(
                "You can not modify allocation when payment is reconciled with any invoice/bill.")
        common_ids = self.env['common.allocation'].search([('select', '=', True), ('linked_payment_id', '=', payment_id.id)])
        if not common_ids:
            raise UserError(_("Please select any record to process payment."))
        if payment_id:
            res.update({
                'payment_id': payment_id.id,
                'current_payment_amount': payment_id.amount,
                'total_amount': payment_id.total_amount,
                'remaining_amount': payment_id.remaining_amount,
                'discount_amount': payment_id.discount_amount,
                'sale_tax': payment_id.sale_tax,
                'writeoff_amount': payment_id.writeoff_amount,
                'sale_tax_account_id': payment_id.sale_tax_account_id.id,
            })
        return res

    def action_process_payment(self):
        payment_id = self.payment_id
        if payment_id:
            payment_id.sale_tax_account_id = self.sale_tax_account_id.id
            payment_id.action_process_payment_allocation()

       # call payment action
        view_id = self.env.ref('account.view_account_payment_form')
        action = self.env.ref("account.action_account_payments")
        result = action.read()[0]
        result['domain'] = [('id', '=', payment_id.id)]
        result['res_id'] = payment_id.id
        result['views'] = [(view_id.id, 'form')]
        return result


