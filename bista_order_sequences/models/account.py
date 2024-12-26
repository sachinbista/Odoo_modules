
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    pricelist_id = fields.Many2one("product.pricelist", string="Price List")

    @api.model
    def create(self, vals):
        # Original Code
        # sale_order_obj = self.env['sale.order']
        # res = super(AccountMove, self).create(vals)
        # if res.invoice_origin:
        #     sale_order_id = sale_order_obj.search([('name', 'like', res.invoice_origin)], limit=1)
        #     if sale_order_id:
        #         res.sale_order_id = sale_order_id.id
        #         if sale_order_id.pricelist_id:
        #             res.pricelist_id = sale_order_id.pricelist_id.id
        sale_order_obj = self.env['sale.order']
        if vals.get('invoice_origin', ''):
            so = sale_order_obj.search([('name', 'like', vals['invoice_origin'])], limit=1)
            if so:
                vals.update({
                    'sale_order_id': so.id,
                    'pricelist_id': so.pricelist_id and so.pricelist_id.id or False

                })
        return super(AccountMove, self).create(vals)

    def action_post(self):
        # Original Code
        # res = super(AccountMove, self).action_post()
        # if len(self._ids) > 1 or self.move_type in ['in_invoice', 'in_refund', 'out_refund']:
        #     return res

        # invoice_count = len(self.sale_order_id.invoice_ids.filtered(lambda invoice: invoice.id != self.id))
        # print("\n _________self.sale_order_id________",self.sale_order_id)
        # if self.sale_order_id:
        #     order_number = self.sale_order_id.name.replace(self.env.ref('sale.seq_sale_order').prefix, '')
        #     order_number = order_number + '-' + str(invoice_count + 1)
        #     invoice_id = self.sudo().search([('name','=',order_number)])

        #     if invoice_id:
        #         print("\n ________-invoice_id_____-",invoice_id)
        #     else:
        #         print("\n __________else______\n")
        #         self.sudo().write({'name': 'INV/' + order_number})

        # self.sudo().write({'payment_reference': self.name})

        # if self.invoice_payment_term_id and self.invoice_payment_term_id.id != self.env.ref('account.account_payment_term_immediate').id:
        #     return self.action_invoice_sent()
        res = super(AccountMove, self).action_post()
        if len(self._ids) > 1 or self.move_type in ['in_invoice', 'in_refund', 'out_refund']:
            return res

        if self.sale_order_id:
            invoice_count = self.sale_order_id.invoice_count
            order_number = self.sale_order_id.name.replace(self.env.ref('sale.seq_sale_order').prefix, '')
            order_number = f"{order_number}-{invoice_count}"
            invoice_name = self.name
            group_names = invoice_name.split('/')
            # update last sequence to SO sequence
            group_names[-1] = order_number
            invoice_name = '/'.join(group_names)
            self.sudo().write({
                'name': invoice_name,
                'payment_reference': invoice_name
            })

        if self.invoice_payment_term_id and self.invoice_payment_term_id.id != self.env.ref('account.account_payment_term_immediate').id:
            return self.action_invoice_sent()

        return res


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + ", move.pricelist_id as pricelist_id"
