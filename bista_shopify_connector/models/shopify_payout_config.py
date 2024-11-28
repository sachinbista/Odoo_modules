##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class ShopifyPayoutconfig(models.Model):

    _name = "shopify.payout.config"
    _description = "Shopify Payout Configuration"

    shopify_config_id = fields.Many2one(
        'shopify.config', string="Shopify Config")
    account_id = fields.Many2one('account.account', string="Account",
                                 help="The accountwhich will be use for the invoice.")
    balance_transaction_type = fields.Selection(
        [('charge', 'Charge'), ('refund', 'Refund'), ('dispute', 'Dispute'),
         ('reserve', 'Reserve'), ('adjustment',
                                  'Adjustment'), ('credit', 'Credit'),
         ('debit', 'Debit'), ('payout',
                              'Payout'), ('payout_failure', 'Payout Failure'),
         ('payout_cancellation', 'Payout Cancellation'), ('fees', 'Fees'), ('payment_refund', 'Payment Refund')],
        help="The type of the balance transaction", string="Balance Transaction Type")
