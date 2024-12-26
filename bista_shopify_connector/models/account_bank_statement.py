##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields

class AccountBankStatement(models.Model):
    
    _inherit = 'account.bank.statement'

    shopify_payout_ref = fields.Char(string='Shopify Payout Reference')

class AccountBankStatementLine(models.Model):
    
    _inherit = "account.bank.statement.line"

    shopify_transaction_id = fields.Char("Shopify Transaction")
    shopify_transaction_type = fields.Selection(
        [('charge', 'Charge'), ('refund', 'Refund'), ('dispute', 'Dispute'),
         ('reserve', 'Reserve'), ('adjustment', 'Adjustment'), ('credit', 'Credit'),
         ('debit', 'Debit'), ('payout', 'Payout'), ('payout_failure', 'Payout Failure'),
         ('payout_cancellation', 'Payout Cancellation'), ('fees', 'Fees'), ('payment_refund','Payment Refund')],
        help="The type of the balance transaction", string="Balance Transaction Type")
