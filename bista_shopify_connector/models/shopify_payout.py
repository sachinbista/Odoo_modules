##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

import logging

from datetime import datetime
from odoo import models, fields, tools, _
from odoo.exceptions import ValidationError
from .. import shopify

_logger = logging.getLogger('Shopify Payout')

class ShopifyPayment(models.Model):

    _name = "shopify.payout"
    _description = "Shopify Payout"

    name = fields.Char(size=256)
    shopify_config_id = fields.Many2one('shopify.config', string="Shopify Configuration")
    payout_ref_id = fields.Char(string="Payout Reference",help="The unique reference of the payout")
    date_payout = fields.Date(help="The date the payout was issued.")
    payout_transaction_ids = fields.One2many('shopify.payout.line', 'payout_id',
                                             string="Payout transaction lines")
    currency_id = fields.Many2one('res.currency', string='Currency',help="currency of the payout.")
    amount_total = fields.Float(string="Total Amount", help="The total amount of the payout.")
    # statement_id = fields.Many2one('account.bank.statement', string="Bank Statement")
    payout_status = fields.Selection([('scheduled', 'Scheduled'), ('in_transit', 'In Transit'), ('paid', 'Paid'),
                                      ('failed', 'Failed'), ('cancelled', 'Cancelled')],
                                     help="The transfer status of the payout. The value will be one of the following\n"
                                          "- Scheduled:  The payout has been created and had transactions assigned to"
                                          "it, but it has not yet been submitted to the bank\n"
                                          "- In Transit: The payout has been submitted to the bank for processing.\n"
                                          "- Paid: The payout has been successfully deposited into the bank.\n"
                                          "- Failed: The payout has been declined by the bank.\n"
                                          "- Cancelled: The payout has been canceled by Shopify")
    status = fields.Selection([('draft', 'Draft'), ('partially_generated', 'Partially Generated'),
                              ('generated', 'Generated'), ('partially_processed', 'Partially Processed'),
                              ('processed', 'Processed'), ('validated', 'Validated')], string="Status",
                              default="draft")

    def return_data(self):
        payouts =  {
            "payouts": 
                [{
                    "id": 854088011,
                    "status": "scheduled",
                    "date": "2013-11-01",
                    "currency": "USD",
                    "amount": "43.12",
                    "summary": {
                        "adjustments_fee_amount": "0.12",
                        "adjustments_gross_amount": "2.13",
                        "charges_fee_amount": "1.32",
                        "charges_gross_amount": "45.52",
                        "refunds_fee_amount": "-0.23",
                        "refunds_gross_amount": "-3.54",
                        "reserved_funds_fee_amount": "0.00",
                        "reserved_funds_gross_amount": "0.00",
                        "retried_payouts_fee_amount": "0.00",
                        "retried_payouts_gross_amount": "0.00"
                    }
                },
                {
                  "id": 512467833,
                  "status": "failed",
                  "date": "2013-11-01",
                  "currency": "USD",
                  "amount": "43.12",
                  "summary": {
                        "adjustments_fee_amount": "0.12",
                        "adjustments_gross_amount": "2.13",
                        "charges_fee_amount": "1.32",
                        "charges_gross_amount": "45.52",
                        "refunds_fee_amount": "-0.23",
                        "refunds_gross_amount": "-3.54",
                        "reserved_funds_fee_amount": "0.00",
                        "reserved_funds_gross_amount": "0.00",
                        "retried_payouts_fee_amount": "0.00",
                        "retried_payouts_gross_amount": "0.00"
                  }
                }]
            }
        return payouts.get('payouts')

    def shopify_import_payouts(self, shopify_config):
        """This method is used to create queue and queue line for payouts"""
        shopify_config.check_connection()
        # shopify_payout_list = self.fetch_all_shopify_orders(shopify_config, shopify_config.last_payout_import_date)
        shopify_payout_list = self.return_data()
        if shopify_payout_list:
            for shopify_payouts in tools.split_every(250, shopify_payout_list):
                for payout in shopify_payouts:
                    currency_id = self.env['res.currency'].search([('name','=',payout.get('currency'))])
                    payout_id = self.env['shopify.payout'].create({
                            'name':self.env['ir.sequence'].next_by_code('shopify.payout') or 'New',
                            'payout_ref_id': str(payout.get('id')),
                            'payout_status':payout.get('status'),
                            'date_payout':payout.get('date'),
                            'shopify_config_id':shopify_config.id,
                            'currency_id': currency_id.id,
                            'amount_total':payout.get('amount')
                        })
                    line_data = self.payout_transaction_ids.get_payout_line()
                    self.payout_transaction_ids.create_shopify_payout_lines(line_data)
        key_name = 'shopify_config_%s' % (str(shopify_config.id))
        parameter_id = self.env['ir.config_parameter'].search([('key', '=', key_name)])
        shopify_config.get_update_value_from_config(
            operation='write', field='last_payout_import_date', shopify_config_id=shopify_config,
            field_value=str(datetime.now().strftime('%Y/%m/%d %H:%M:%S')), parameter_id=parameter_id)
        return True


class ShopifyPayoutLine(models.Model):

    _name = "shopify.payout.line"
    _description = "Shopify Payout Lines"
    _rec_name = "transaction_id"

    payout_id = fields.Many2one('shopify.payout', string="Payout ID", ondelete="cascade")
    transaction_id = fields.Char(string="Transaction ID", help="The unique identifier of the transaction.")
    source_order_id = fields.Char(string="Order Reference ID", help="The id of the Order that this transaction  "
                                                                    "ultimately originated from")
    transaction_type = fields.Selection(
        [('charge', 'Charge'), ('refund', 'Refund'), ('dispute', 'Dispute'),
         ('reserve', 'Reserve'), ('adjustment', 'Adjustment'), ('credit', 'Credit'),
         ('debit', 'Debit'), ('payout', 'Payout'), ('payout_failure', 'Payout Failure'),
         ('payout_cancellation', 'Payout Cancellation'), ('fees', 'Fees'), ('payment_refund','Payment Refund')],
        help="The type of the balance transaction", string="Balance Transaction Type")
    currency_id = fields.Many2one('res.currency', string='Currency', help="currency code of the payout.")
    source_type = fields.Selection(
        [('charge', 'Charge'), ('refund', 'Refund'), ('dispute', 'Dispute'),
         ('reserve', 'Reserve'), ('adjustment', 'Adjustment'), ('payout', 'Payout'), ],
        help="The type of the balance transaction", string="Resource Leading Transaction")
    amount = fields.Float(string="Amount", help="The gross amount of the transaction.")
    fee = fields.Float(string="Fees", help="The total amount of fees deducted from the transaction amount.")
    net_amount = fields.Float(string="Net Amount", help="The net amount of the transaction.")
    order_id = fields.Many2one('sale.order', string="Order Reference")
    processed_date = fields.Datetime("Processed Date")


    def create_shopify_payout_lines(self,line_data):
        for payout_line in line_data:
            payout_line_id = self.env['shopify.payout.line'].create({
                            'transaction_id':payout_line.get('id'),
                            'payout_id':payout_line.get('id'),
                            'source_type':'refund'
                })
            return payout_line
            # if payout_line.get()



    def get_payout_line(self):
        data = {
                  "transactions": [
                    {
                      "id": 699519475,
                      "type": "debit",
                      "test": False,
                      "payout_id": 854088011,
                      "payout_status": "paid",
                      "currency": "USD",
                      "amount": "-50.00",
                      "fee": "0.00",
                      "net": "-50.00",
                      "source_id": 460709370,
                      "source_type": "adjustment",
                      "source_order_id": False,
                      "source_order_transaction_id": False,
                      "processed_at": "2022-02-04T17:14:40-05:00"
                    },
                    {
                      "id": 77412310,
                      "type": "credit",
                      "test": False,
                      "payout_id": 854088011,
                      "payout_status": "paid",
                      "currency": "USD",
                      "amount": "50.00",
                      "fee": "0.00",
                      "net": "50.00",
                      "source_id": 374511569,
                      "source_type": "Payments::Balance::AdjustmentReversal",
                      "source_order_id": False,
                      "source_order_transaction_id": False,
                      "processed_at": "2022-02-04T17:14:40-05:00"
                    },
                    {
                      "id": 746296004,
                      "type": "charge",
                      "test": False,
                      "payout_id": 512467833,
                      "payout_status": "paid",
                      "currency": "USD",
                      "amount": "10.00",
                      "fee": "2.00",
                      "net": "8.00",
                      "source_id": 746296004,
                      "source_type": "charge",
                      "source_order_id": 625362839,
                      "source_order_transaction_id": 890672011,
                      "processed_at": "2022-02-03T17:14:40-05:00"
                    },
                    {
                      "id": 515523000,
                      "type": "charge",
                      "test": False,
                      "payout_id": 512467833,
                      "payout_status": "paid",
                      "currency": "USD",
                      "amount": "11.50",
                      "fee": "0.65",
                      "net": "10.85",
                      "source_id": 1006917261,
                      "source_type": "Payments::Refund",
                      "source_order_id": 217130470,
                      "source_order_transaction_id": 1006917261,
                      "processed_at": "2022-02-03T17:14:40-05:00"
                    },
                   ]
                  }
        return data.get('transactions')