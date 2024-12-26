from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'




    def _get_reconcile_entry(self):
        reconcile_line_ids = {}
        reconcile_line_list = []
        reconcile_pay_list = []
        pay_term_lines = self.line_ids \
            .filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
        if pay_term_lines.matched_debit_ids:
            for line in self.move_id.line_ids:
                bill_ids = self.move_id.line_ids \
                    .filtered(lambda line: line.account_id.account_type in ('liability_payable'))
                if not bill_ids:
                    pay_term_lines = line.filtered(lambda line: line.account_type in ('asset_receivable'))
                    if pay_term_lines:
                        amount=line.credit - self.amount
                        if amount > 0 :
                            move_line_ids=self.move_id.line_ids.filtered(lambda line: line.debit == amount)
                            if move_line_ids:
                                reconcile_line_ids = {
                                    'inv_date':self.date,
                                    'write_off':move_line_ids.name,
                                    'inv_ref':'',
                                    'amount':amount
                                }
                                reconcile_line_list.append(reconcile_line_ids)

                    # else:
                    #     # if line.debit:
                    #     reconcile_line_ids = {
                    #         'inv_date': line.move_id.date,
                    #         'inv_name': line.move_id.name,
                    #         'inv_ref': '',
                    #         'amount': - line.debit
                    #     }
                    #     reconcile_pay_list.append(reconcile_line_ids)
                else:
                    pay_term_lines = line.filtered(lambda line: line.account_type in ('liability_payable'))
                    if pay_term_lines:
                        if line.debit:
                            amount = line.debit - self.amount
                        if line.credit:
                            amount = line.credit - self.amount
                        if amount > 0:
                            if line.debit:
                                move_line_ids = self.move_id.line_ids.filtered(lambda line: line.credit == amount)
                            if line.credit:
                                move_line_ids = self.move_id.line_ids.filtered(lambda line: line.debit == amount)
                            if move_line_ids:
                                reconcile_line_ids = {
                                    'inv_date': move_line_ids.date,
                                    'write_off': move_line_ids.name,
                                    'inv_ref': '',
                                    'amount': amount
                                }
                                reconcile_line_list.append(reconcile_line_ids)

                    # else:
                    #     # if line.debit:
                    #     reconcile_line_ids = {
                    #         'inv_date': line.move_id.date,
                    #         'inv_name': line.move_id.name,
                    #         'inv_ref': '',
                    #         'amount': - line.credit
                    #     }
                    #     reconcile_pay_list.append(reconcile_line_ids)

        if pay_term_lines.matched_credit_ids:
            for line in self.move_id.line_ids:
                bill_ids = self.move_id.line_ids \
                    .filtered(lambda line: line.account_id.account_type in ('liability_payable'))
                if not bill_ids:
                    pay_term_lines = line.filtered(lambda line: line.account_type in ('asset_receivable'))
                    if pay_term_lines:
                        amount = line.debit - self.amount
                        if amount > 0:
                            move_line_ids = self.move_id.line_ids.filtered(lambda line: line.credit == amount)
                            if move_line_ids:
                                reconcile_line_ids = {
                                    'inv_date': move_line_ids.date,
                                    'write_off': move_line_ids.name,
                                    'inv_ref': '',
                                    'amount': amount
                                }
                                reconcile_line_list.append(reconcile_line_ids)

                else:
                    pay_term_lines = line.filtered(lambda line: line.account_type in ('liability_payable'))
                    if pay_term_lines:
                        amount = line.debit - self.amount
                        if amount > 0:
                            move_line_ids = self.move_id.line_ids.filtered(lambda line: line.credit == amount)
                            if move_line_ids:
                                reconcile_line_ids = {
                                    'inv_date': move_line_ids.date,
                                    'write_off': move_line_ids.name,
                                    'inv_ref': '',
                                    'amount': amount
                                }
                                reconcile_line_list.append(reconcile_line_ids)
        # reconcile_line_ids = {}
        # reconcile_line_list = []
        # reconcile_pay_list = []
        # due_amount = 0
        # for line in self.move_id.line_ids:
        #
        #     bill_ids = self.move_id.line_ids \
        #         .filtered(lambda line: line.account_id.account_type in ('liability_payable'))
        #     if not bill_ids:
        #         pay_term_lines = line.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
        #         if pay_term_lines:
        #             reconcile_line_ids = {
        #                 'inv_date': line.move_id.date,
        #                 'inv_name': '',
        #                 'inv_ref': line.move_id.ref,
        #                 'amount': line.credit
        #             }
        #             reconcile_line_list.append(reconcile_line_ids)
        #
        #         else:
        #             # if line.debit:
        #             reconcile_line_ids = {
        #                 'inv_date': line.move_id.date,
        #                 'inv_name': line.move_id.name,
        #                 'inv_ref': '',
        #                 'amount': - line.debit
        #             }
        #             reconcile_pay_list.append(reconcile_line_ids)
        #     else:
        #         pay_term_lines = line.filtered(
        #             lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
        #         if pay_term_lines:
        #             reconcile_line_ids = {
        #                 'inv_date': line.move_id.date,
        #                 'inv_name': '',
        #                 'inv_ref': line.move_id.ref,
        #                 'amount':   line.debit
        #             }
        #             reconcile_line_list.append(reconcile_line_ids)
        #
        #         else:
        #             # if line.debit:
        #             reconcile_line_ids = {
        #                 'inv_date': line.move_id.date,
        #                 'inv_name': line.move_id.name,
        #                 'inv_ref': '',
        #                 'amount': - line.credit
        #             }
        #             reconcile_pay_list.append(reconcile_line_ids)
        final_list = reconcile_line_list + reconcile_pay_list
        return final_list
