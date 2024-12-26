from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    fds_payment_require = fields.Boolean(string="Payment Required",readonly=True,copy=False)
    # fds_web_payment_require = fields.Boolean(string="Payment Require",copy=False)



    # def action_preview_sale_order(self):
    #     self.ensure_one()
    #     if self.fds_payment_require:
    #         self.fds_web_payment_require = True
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'target': 'self',
    #         'url': self.get_portal_url(),
    #     }

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def create(self, vals):
        payment = super(AccountPayment, self).create(vals)
        order_id = vals.get('sale_order_id_payment')
        if order_id:
            sale_order = self.env['sale.order'].browse(order_id)
            if sale_order and sale_order.fds_payment_require:
                sale_order.fds_payment_require = False
        return payment

