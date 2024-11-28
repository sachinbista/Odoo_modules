from odoo import models, api,fields,_


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        account_payment_register_obj = self.env['account.payment.register'].sudo()
        stock_landed_cost_obj = self.env['stock.landed.cost'].sudo()
        move_reverse = self.env['account.move.reversal'].sudo()

        if self.company_id.is_transit:
            # create reverse journal entry and landed cost
            for transit_move in self.purchase_id.transit_move_ids:
                cost_line = transit_move.line_ids.filtered(lambda x: x.product_id)
                if cost_line:
                    landed_cost = stock_landed_cost_obj.create({
                        "picking_ids": [(4, self.id)],
                        'cost_lines': [(0, 0, {
                            'product_id': l.product_id.id,
                            'name': l.product_id.name,
                            'account_id': l.product_id.product_tmpl_id.get_product_accounts()[
                                    'stock_input'].id,
                            'price_unit': l.credit,
                            'split_method': l.product_id.split_method_landed_cost or 'equal',
                        }) for l in cost_line]
                    })
                    landed_cost.button_validate()

                reverse_wizard = move_reverse.create({
                    'journal_id': transit_move.journal_id.id,
                    'move_ids': [[4, transit_move.id]],
                    'reason': 'Transit Entry Reversal',
                    'date': fields.Date.today(),
                })
                reverse_wizard.refund_moves()

        if self.purchase_id:
            landed_cost_ids = stock_landed_cost_obj.search([('purchase_id','=',self.purchase_id.id),('state','=','draft')])
            for landed_cost in landed_cost_ids:
                landed_cost.write({'picking_ids': [(4, self.id)]})
                landed_cost.button_validate()
                if not landed_cost.vendor_bill_id:
                    bill_obj = landed_cost.create_landed_bill(self.purchase_id)
                    bill_obj.internal_order_ref = landed_cost.internal_order_ref
                    landed_cost.vendor_bill_id = bill_obj.id
                    bill_obj.action_post()
                    payment_journal_id = self.env['account.journal'].sudo().search([
                        ('is_vendor_journal', '=', True),
                        ('company_id', '=', self.company_id.id)])
                    payment_wizard = account_payment_register_obj.with_context(
                        active_ids=bill_obj.line_ids.ids,
                        active_model='account.move.line', default_journal_id=payment_journal_id,
                        company_id=self.company_id.id).create({})
                    payment = payment_wizard.sudo().action_create_payments()
                    res_id = payment.get('res_id')
                    if res_id:
                        payment_obj = self.env['account.payment'].sudo().search([('id', '=', res_id)])
                        payment_obj.internal_order_ref = landed_cost.internal_order_ref
        return res
