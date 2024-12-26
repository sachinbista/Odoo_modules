from odoo import models, fields, api


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    # @api.depends('date', 'currency_id', 'payment_ids.amount')
    # def _compute_amount(self):
    #     """override to handle discount_lines for _seek_for_lines method"""
    #     for batch in self:
    #         currency = batch.currency_id or batch.journal_id.currency_id or self.env.company.currency_id
    #         date = batch.date or fields.Date.context_today(self)
    #         amount = 0
    #         for payment in batch.payment_ids:
    #             liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = payment._seek_for_lines()
    #             for line in liquidity_lines:
    #                 if line.currency_id == currency:
    #                     amount += line.amount_currency
    #                 else:
    #                     amount += line.company_currency_id._convert(
    #                         line.balance, currency, line.company_id, date)
    #         batch.amount = amount

    @api.depends('currency_id', 'payment_ids.amount')
    def _compute_from_payment_ids(self):
        for batch in self:
            amount_currency = 0.0
            amount_residual = 0.0
            amount_residual_currency = 0.0
            for payment in batch.payment_ids:
                liquidity_lines, counterpart_lines, writeoff_lines, discount_lines, sale_tax_lines = payment._seek_for_lines()
                for line in liquidity_lines:
                    amount_currency += line.amount_currency
                    amount_residual += line.amount_residual
                    amount_residual_currency += line.amount_residual_currency

            batch.amount_residual = amount_residual
            batch.amount = amount_currency
            batch.amount_residual_currency = amount_residual_currency