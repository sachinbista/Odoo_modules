##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo.tools.safe_eval import safe_eval
from .. import shopify
from datetime import datetime, timedelta
from odoo import fields, models, tools, _, api
from odoo.exceptions import AccessError, ValidationError,UserError
from odoo.tools.float_utils import float_round
from pyactiveresource.util import xml_to_dict
import logging
_logger = logging.getLogger(__name__)  # Need for message in console.


class AccountpaymentCustom(models.Model):
    _name = "account.payment.custom"

    invoice_id = fields.Many2one('account.move')
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)


    def create_payment(self):
        invoice_ids = self.env['account.move'].search(
            [('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'partial')),('company_id','=',self.shopify_config_id.default_company_id.id),('move_type', '=', 'out_invoice')],limit=50)
        # invoice_ids =self.env['account.move'].search([('id','=',61029)])
        _logger.info("----------------------------invoice_ids {}".format(invoice_ids))
        for rec in self:
            for invoice_id in invoice_ids:
                _logger.info("----------------------------invoice_ids {}".format(invoice_id))

                print("invoice_idinvoice_idinvoice_idinvoice_idinvoice_id",invoice_id)
                self.shopify_config_id.check_connection()
                shopify_queue_line = self.env['shopify.queue.job.line']
                # shopify_order = int(rec.invoice_id.shopify_order_id)
                # queue_line = shopify_queue_line.search([('shopify_id','=',invoice_id.shopify_order_id)])
                # for queue in queue_line:
                #     if queue.state == 'failed':
                #         print("aaaaaaaaaaaaaa",queue)
                #         order_dict = safe_eval(queue.record_data)
                #         # rec.invoice_id.sale_order_id.create_shopify_direct_payment(
                #         #     self.shopify_config_id, rec.invoice_id.sale_order_id, order_dict, self.invoice_id.partner_id)
                currency_obj = self.env['res.currency']
                error_log_env = self.env['shopify.error.log']
                financial_status = invoice_id.sale_order_id.financial_workflow_id.financial_status
                shop_order_id = invoice_id.sale_order_id.shopify_order_id
                order_name = invoice_id.sale_order_id.shopify_order_name
                shop_error_log_id = self.env.context.get('shopify_log_id', False)
                queue_line_id = self.env.context.get('queue_line_id', False)
                payment_obj = self.env['account.payment']
                payment_method_in = self.env.ref("account.account_payment_method_manual_in")
                # TODO: if want to set with batch payment type
                # payment_method_in = self.env.ref(
                #     'account_batch_payment.account_payment_method_batch_deposit')
                # try:
                if invoice_id.sale_order_id and financial_status in ('paid', 'partially_paid',
                                                        'refunded', 'partially_refunded'):
                    # TODO: need to add time.sleep for multiple call error
                    transactions = shopify.Transaction().find(order_id=shop_order_id)
                    print("qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",transactions)

                    # transactions = shopify.Transaction.find(order_id=shop_order)
                    payment_date = invoice_id.sale_order_id.date_order or False
                    for transaction in transactions:
                        transaction_data = transaction.attributes
                        transaction_id = transaction_data.get('id')
                        status = transaction_data.get('status')
                        kind = transaction_data.get('kind')
                        msg = transaction_data.get('message')
                        gateway = transaction_data.get('gateway')
                        print("gateway--------------------",gateway)
                        existing_payment_id = payment_obj.search(
                            [('shopify_transaction_id', '=', str(transaction_id)),
                             ('shopify_config_id', '=', self.shopify_config_id.id),
                             ("state", '!=', 'cancelled'),
                             ], limit=1)
                        if existing_payment_id:
                            continue
                        if status == 'success' and kind in ['sale', 'capture']:
                            amount = transaction_data.get('amount')
                            local_inv_datetime = datetime.strptime(
                                transaction_data.get('processed_at')[:19],
                                '%Y-%m-%dT%H:%M:%S')
                            local_time = transaction_data.get('processed_at')[
                                         20:].split(":")
                            if transaction_data.get('processed_at')[19] == "+":
                                local_datetime = local_inv_datetime - timedelta(
                                    hours=int(local_time[0]),
                                    minutes=int(local_time[1]))
                            else:
                                local_datetime = local_inv_datetime + timedelta(
                                    hours=int(local_time[0]),
                                    minutes=int(local_time[1]))
                            # Set payment date here
                            payment_date = (str(local_datetime)[:19])
                            # Check payment currency
                            tcurrency = transaction_data.get('currency')
                            tcurrency_id = currency_obj.search([('name', '=', tcurrency)], limit=1)
                            if not tcurrency_id:
                                error_message = "Currency %s not found in the system for transaction %s. " \
                                                "Please contact system Administrator." % (
                                                    tcurrency, transaction_id)
                                error_log_env.create_update_log(
                                    shop_error_log_id=shop_error_log_id,
                                    shopify_log_line_dict={'error': [
                                        {'error_message': error_message,
                                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

                                continue
                            # TODO: Update it once we implement workflow
                            auto_workflow_id = invoice_id.sale_order_id.auto_workflow_id
                            journal_id = invoice_id.sale_order_id.shopify_payment_gateway_id.pay_journal_id
                            if not journal_id:
                                error_message = 'Payment journal not found!'
                                error_log_env.create_update_log(
                                    shop_error_log_id=shop_error_log_id,
                                    shopify_log_line_dict={'error': [
                                        {'error_message': error_message,
                                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                continue
                            payment_method_id = auto_workflow_id.in_pay_method_id
                            if not invoice_id.partner_id.commercial_partner_id:
                                invoice_id._compute_commercial_partner()
                            payment_type = 'inbound'
                            if kind == 'refund':
                                payment_type = 'outbound'
                            invoice = invoice_id.sale_order_id.invoice_ids.filtered(lambda
                                                                           i: i.state != 'cancel' and i.move_type == 'out_invoice' and i.payment_state != 'paid')
                            if len(invoice) > 1:
                                inv_ids = invoice.ids
                            else:
                                inv_ids = [invoice.id]
                            # payment_vals = {'amount': amount,
                            #                 'date': payment_date,
                            #                 'payment_reference': rec.invoice_id.sale_order_id.name,
                            #                 'partner_id': rec.invoice_id.partner_id.id,
                            #                 'partner_type': 'customer',
                            #                 'currency_id': tcurrency_id.id,
                            #                 'journal_id': journal_id and journal_id.id,
                            #                 'payment_type': payment_type,
                            #                 'shopify_order_id': shop_order_id,
                            #                 'sale_order_id': self.id,
                            #                 'payment_method_id': payment_method_id.id or False,
                            #                 'shopify_transaction_id': transaction_id or False,
                            #                 'shopify_gateway': gateway or False,
                            #                 'shopify_note': msg,
                            #                 'shopify_name': order_name,
                            #                 'shopify_config_id': self.shopify_config_id.id,
                            #                 'move_id': invoice.id}
                            if kind in ['sale', 'refund', 'capture'] and status == 'success':
                                inv_payment_wizard = self.env['account.payment.register']
                                _logger.info("----------------------------payment {}".format(payment_method_id))
                                payment_id = inv_payment_wizard.with_context(active_model='account.move',
                                                                active_ids=[invoice_id.id]).create(
                                    {
                                     'journal_id': journal_id and journal_id.id,
                                     'amount': amount})._create_payments()
                                if payment_id:
                                    payment_id.write({'payment_reference': invoice_id.sale_order_id.name,
                                                      'payment_type': payment_type,
                                                      'shopify_order_id': shop_order_id,
                                                      'sale_order_id': invoice_id.sale_order_id.id,
                                                      'payment_method_id': payment_method_id.id or False,
                                                      'shopify_transaction_id': transaction_id or False,
                                                      'shopify_gateway': gateway or False,
                                                      'shopify_note': msg,
                                                      'shopify_name': order_name,
                                                      'shopify_config_id': self.shopify_config_id.id,
                                                      })
