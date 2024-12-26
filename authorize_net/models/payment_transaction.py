# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import logging
import pprint
from datetime import datetime
import psycopg2
from dateutil.relativedelta import relativedelta

from .authorize_request import AuthorizeAPI
from odoo import fields, models, api, _
from odoo.addons.authorize_net.models import misc
from odoo.tools import str2bool

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    transaction_type = fields.Selection([
        ('debit', 'Debit'),
        ('credit', 'Credit')], 'Transaction Type', copy=False)
    refund_amount = fields.Monetary(string="Refund Amount", copy=False)
    echeck_transaction = fields.Boolean(help='Technical field for check is echeck transaction or not?', copy=False)
    company_id = fields.Many2one('res.company', related='provider_id.company_id',
            string='Company', index=True, copy=False)

    def _reconcile_after_done(self):
        """ Override of payment to automatically confirm quotations and generate invoices. """
        if self.env.context.get('bypass_confirm_and_email'):
            # confirmed_orders = self._check_amount_and_confirm_order()
            # confirmed_orders._send_order_confirmation_mail()
            # (self.sale_order_ids - confirmed_orders)._send_payment_succeeded_for_order_mail()

            auto_invoice = str2bool(
                self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice'))
            if auto_invoice:
                # Invoice the sale orders in self instead of in confirmed_orders to create the invoice
                # even if only a partial payment was made.
                self._invoice_sale_orders()
            super()._reconcile_after_done()
            if auto_invoice:
                # Must be called after the super() call to make sure the invoice are correctly posted.
                self._send_invoice()
        else:
            super()._reconcile_after_done()

    def _finalize_post_processing(self):
        """ Trigger the final post-processing tasks and mark the transactions as post-processed.

        :return: None
        """
        if self.env.context.get('bypass_confirm_and_email'):
            self.filtered(lambda tx: tx.operation != 'validation').with_context(bypass_confirm_and_email=True)._reconcile_after_done()
            self.is_post_processed = True
        else:
            super()._finalize_post_processing()


    def _cron_finalize_post_processing(self):
        """ Finalize the post-processing of recently done transactions not handled by the client.

        :return: None
        """
        if self.env.context.get('bypass_confirm_and_email'):
            txs_to_post_process = self
            if not txs_to_post_process:
                # Don't try forever to post-process a transaction that doesn't go through. Set the limit
                # to 4 days because some providers (PayPal) need that much for the payment verification.
                retry_limit_date = datetime.now() - relativedelta.relativedelta(days=4)
                # Retrieve all transactions matching the criteria for post-processing
                txs_to_post_process = self.search([
                    ('state', '=', 'done'),
                    ('is_post_processed', '=', False),
                    ('last_state_change', '>=', retry_limit_date),
                ])
            for tx in txs_to_post_process:
                try:
                    tx.with_context(bypass_confirm_and_email=True)._finalize_post_processing()
                    self.env.cr.commit()
                except psycopg2.OperationalError:
                    self.env.cr.rollback()  # Rollback and try later.
                except Exception as e:
                    _logger.exception(
                        "encountered an error while post-processing transaction with reference %s:\n%s",
                        tx.reference, e
                    )
                    self.env.cr.rollback()
        else:
            return super()._cron_finalize_post_processing()

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        if self.provider_code != 'authorize':
            return

        authorize_API = AuthorizeAPI(self.provider_id)
        # Convert Currency Amount
        from_currency_id = self.currency_id or self.company_id.currency_id
        to_currency_id = self.provider_id.journal_id.currency_id or self.provider_id.journal_id.company_id.currency_id
        currency_amount = self.amount
        if from_currency_id and to_currency_id and from_currency_id != to_currency_id:
            currency_amount = from_currency_id._convert(self.amount, to_currency_id, self.provider_id.journal_id.company_id, fields.Date.today())
            rounded_amount = round(currency_amount, self.currency_id.decimal_places)
        else:
            rounded_amount = round(self.amount, self.currency_id.decimal_places)

        res_content = authorize_API.capture(self.provider_reference, rounded_amount)
        _logger.info(
            "capture request response for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(res_content)
        )
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_notification_data('authorize', feedback_data)

        # For reconcile the payment
        if not self.payment_id: self.with_context(bypass_confirm_and_email=True)._cron_finalize_post_processing()
        if self.payment_id and self.provider_id.code == 'authorize':
            self.payment_id.authorize_payment_type = self.provider_id and self.provider_id.authorize_payment_method_type or ''
        if self.payment_id and self.payment_id.state == 'draft' and self.state == 'done':
            self.payment_id.action_post()
            (self.payment_id.line_ids + self.invoice_ids.line_ids).filtered(
                lambda line: line.account_id == self.payment_id.destination_account_id
                and not line.reconciled
            ).reconcile()
            self.is_post_processed = True

    def get_payment_transaction_details(self):
        """ Send a get transaction to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        if self.provider_code != 'authorize':
            return False

        if self.provider_reference and self.provider_id:
            authorize_api = AuthorizeAPI(self.provider_id)
            response = authorize_api.get_transaction_details(self.provider_reference)
            response.update(resultCode=response.get('messages').get('resultCode'))
            if response.get('transaction', {}).get('payment', {}).get('creditCard', False):
                response.update(x_cardNumber=response.get('transaction', {}).get('payment', {}).get('creditCard', {}).get('cardNumber', False))
            else:
                response.update(x_cardNumber=response.get('transaction', {}).get('payment', {}).get('bankAccount', {}).get('accountNumber', False))
            if response.get('resultCode') == 'Ok' and response.get('x_cardNumber'):
                return response['x_cardNumber'][4:]
            return False

    def create_payment_vals(self, trans_id=None, authorize_partner=None, authorize_payment_type='credit_card'):
        """ Create a payment of Authorize.Net payment transaction.

        Note: self.ensure_one()

        :trans_id: Authorize.Net transaction id
        :authorize_partner: Customer Profile Linked with Partner
        :authorize_payment_type: Payment Type
        :return:
        """
        self.ensure_one()
        payment_vals = {
            'amount': self.amount,
            'payment_type': 'inbound' if self.transaction_type == 'debit' else 'outbound',
            'partner_type': 'customer',
            'date': fields.Date.today(),
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'transaction_id': trans_id,
            'journal_id': self.provider_id.journal_id.id,
            'company_id': self.provider_id.company_id.id,
            'payment_token_id': self.token_id and self.token_id.id or None,
            'payment_transaction_id': self.id,
            'ref': self.reference,
            'customer_profile_id': authorize_partner.customer_profile_id,
            'merchant_id': authorize_partner.merchant_id,
            'authorize_payment_type': authorize_payment_type,
            'transaction_type': 'auth_capture'
        }
        payment_id = self.env['account.payment'].sudo().create(payment_vals)
        return payment_id

    def _process_feedback_data(self, data):
        super(PaymentTransaction, self)._process_feedback_data(data=data)
        self = self.sudo()

        response_content = data.get('response')
        if response_content and self.state == 'done' and not self.payment_id:
            self._cron_finalize_post_processing()
        if response_content and self.state == 'done' and self.payment_id:
            self.transaction_type = 'debit'
            if self.token_id and self.token_id.customer_profile_id:
                self.payment_id.customer_profile_id = self.token_id.customer_profile_id
            if not self.echeck_transaction and not self.payment_id.authorize_payment_type:
                self.payment_id.authorize_payment_type = 'credit_card'
        return response_content
    
    def _set_pending(self, state_message=None, extra_allowed_states=()):
        """ Update the transactions' state to `pending`.

        :param str state_message: The reason for setting the transactions in the state `pending`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'pending'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        allowed_states = ('draft',)
        target_state = 'pending'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._log_received_message()
        if self.env.context.get('send_payment_succeeded_for_order_mail'):
            for tx in txs_to_process:  # Consider only transactions that are indeed set pending.
                sales_orders = tx.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent'])
                sales_orders.filtered(
                    lambda so: so.state == 'draft'
                ).with_context(tracking_disable=True).action_quotation_sent()
        return txs_to_process


    def _set_authorized(self, state_message=None, extra_allowed_states=()):
        """ Update the transactions' state to `authorized`.

        :param str state_message: The reason for setting the transactions in the state `authorized`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'authorized'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        if self.env.context.get('bypass_confirm_and_email'):
            allowed_states = ('draft', 'pending')
            target_state = 'authorized'
            txs_to_process = self._update_state(
                allowed_states + extra_allowed_states, target_state, state_message
            )
            txs_to_process._log_received_message()
            # self._check_amount_and_confirm_order()
            return txs_to_process
        else:
            super()._set_authorized()


    def prepare_token_values(self, partner, payment_profile, payment, authorize_API):
        """
            # Need to check this method code on Odoo.sh
        """
        card_details = payment.get('creditCard', False)
        bank_details = payment.get('bankAccount', False)
        token_vals = {}
        if card_details:
            token_vals.update(
                provider_id=self.provider_id.id,
                payment_details=str(misc.masknumber(card_details.get('cardNumber'))) or str(misc.masknumber(card_details.get('name'))),
                credit_card_no=str(misc.masknumber(card_details.get('cardNumber'))) or str(misc.masknumber(card_details.get('name'))),
                credit_card_type=card_details.get('cardType').lower(),
                credit_card_code='XXX',
                credit_card_expiration_month='xx',
                credit_card_expiration_year='XXXX',
                partner_id=self.partner_id.id,
                provider_ref=payment_profile,
                authorize_profile=partner,
                customer_profile_id=partner,
                authorize_payment_method_type=self.provider_id.authorize_payment_method_type,
                verified=True,
                authorize_card=True
            )
        else:
            bank_details = authorize_API.get_customer_payment_profile(partner, payment_profile).get('paymentProfile', {}).get('payment', {}).get('bankAccount', {})
            token_vals.update(
                provider_id=self.provider_id.id,
                payment_details=str(misc.mask_account_number(bank_details.get('accountNumber'))),
                acc_number=str(misc.mask_account_number(bank_details.get('accountNumber'))),
                owner_name=bank_details.get('nameOnAccount'),
                routing_number=str(misc.mask_account_number(bank_details.get('routingNumber'))),
                authorize_bank_type=bank_details.get('accountType'),
                partner_id=self.partner_id.id,
                provider_ref=payment_profile,
                authorize_profile=partner,
                customer_profile_id=partner,
                authorize_payment_method_type=self.provider_id.authorize_payment_method_type,
                verified=True,
                authorize_card=True
            )
        return token_vals

    def _get_partner_authorize_profile(self):
        company_id = self.env.company
        authorize_partner_id = False
        if self.provider_id.authorize_payment_method_type == 'credit_card':
            cc_provider_id = self.provider_id
            bank_provider_id = self.env['payment.provider'].sudo().\
                                _get_authorize_provider(company_id=company_id, \
                                    provider_type='bank_account')
            authorize_API = AuthorizeAPI(cc_provider_id)
            authorize_partner_id = self.partner_id.authorize_partner_ids.filtered(lambda x: \
                        x.provider_id and x.provider_id.id == cc_provider_id.id and \
                        x.company_id.id == cc_provider_id.company_id.id)
        else:
            bank_provider_id = self.provider_id
            cc_provider_id = self.env['payment.provider'].sudo().\
                                _get_authorize_provider(company_id=company_id)
            authorize_API = AuthorizeAPI(bank_provider_id)
            if cc_provider_id.authorize_login == bank_provider_id.authorize_login and \
                    cc_provider_id.company_id.id == bank_provider_id.company_id.id:
                authorize_partner_id = self.partner_id.authorize_partner_ids.filtered(lambda x: \
                        x.bank_provider_id and x.bank_provider_id.id == bank_provider_id.id and \
                        x.company_id.id == bank_provider_id.company_id.id)
            else:
                authorize_partner_id = self.partner_id.authorize_partner_ids.filtered(lambda x: \
                        x.provider_id and x.provider_id.id == self.provider_id.id and \
                        x.company_id.id == self.provider_id.company_id.id)
        return authorize_partner_id, authorize_API, cc_provider_id, bank_provider_id

    def _authorize_tokenize(self):
        """
            # Need to check this method code on Odoo.sh
        """
        """ Create a token for the current transaction.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()
        token = False
        customer_profile_ids = False
        company_id = self.env.company

        merchant_id = self.partner_id._get_customer_id('CUST')
        if not self.provider_id or self.provider_id.authorize_login == 'dummy':
            raise ValidationError(_('Please configure your Authorize.Net account'))

        # acquirer_ids =
        # authorize_partner_id, authorize_API, cc_provider_id, bank_provider_id = self._get_partner_authorize_profile()
        if self.provider_id.authorize_payment_method_type == 'credit_card':
            cc_provider_id = self.provider_id
            bank_provider_id = self.env['payment.provider'].sudo()._get_authorize_provider(company_id=company_id, provider_type='bank_account')
            authorize_API = AuthorizeAPI(cc_provider_id)
            authorize_partner_id = self.partner_id.authorize_partner_ids.filtered(lambda x: \
                    x.provider_id and x.provider_id.id == self.provider_id.id and \
                    x.company_id.id == self.provider_id.company_id.id and \
                    x.provider_type == 'credit_card')
        else:
            bank_provider_id = self.provider_id
            cc_provider_id = self.env['payment.provider'].sudo()._get_authorize_provider(company_id=company_id)
            authorize_API = AuthorizeAPI(bank_provider_id)
            if cc_provider_id.authorize_login == bank_provider_id.authorize_login and cc_provider_id.company_id.id == bank_provider_id.company_id.id:
                authorize_partner_id = self.partner_id.authorize_partner_ids.filtered(lambda x: \
                    x.bank_provider_id and x.bank_provider_id.id == self.provider_id.id and \
                    x.company_id.id == self.provider_id.company_id.id and \
                    x.provider_type == 'credit_card')
            else:
                authorize_partner_id = self.partner_id.authorize_partner_ids.filtered(lambda x: \
                    x.provider_id and x.provider_id.id == self.provider_id.id and \
                    x.company_id.id == self.provider_id.company_id.id and \
                    x.provider_type == 'bank_account')

        if not authorize_partner_id:
            cust_profile = authorize_API.create_customer_profile(
                self.partner_id, self.provider_reference, merchant_id
            )
            authorize_partner_id = False
            if cust_profile.get('profile_id') and cust_profile.get('shipping_address_id'):
                # Create a Customer Profile
                customer_profile_vals = {
                    'customer_profile_id': cust_profile['profile_id'],
                    'shipping_address_id': cust_profile['shipping_address_id'],
                    'partner_id': self.partner_id.id,
                    'company_id': company_id.id,
                    'merchant_id': merchant_id,
                    'provider_id': cc_provider_id.id,
                    'cc_provider_id': cc_provider_id.id,
                    'bank_provider_id': bank_provider_id.id,
                    'provider_type': 'credit_card'
                }
                if cc_provider_id and bank_provider_id and \
                    cc_provider_id.authorize_login != bank_provider_id.authorize_login and \
                    self.provider_id.authorize_payment_method_type == 'bank_account':
                    customer_profile_vals.update({
                        'provider_id': bank_provider_id.id,
                        'cc_provider_id': cc_provider_id.id,
                        'bank_provider_id': bank_provider_id.id,
                        'provider_type': 'bank_account'
                    })
                authorize_partner_id = self.env['res.partner.authorize'].create(customer_profile_vals)
            # Create a Token
            token_vals = self.prepare_token_values(authorize_partner_id.customer_profile_id,
                            cust_profile.get('payment_profile_id'),
                            cust_profile.get('payment'),
                            authorize_API)
        else:
            transaction = authorize_API.get_transaction_details(self.provider_reference).get('transaction', {})
            payment = transaction.get('payment', {})
            payment_profile = transaction.get('profile', {}).get('customerPaymentProfileId', False)
            customer_profile_id = authorize_partner_id[0].customer_profile_id
            token_vals = self.prepare_token_values(customer_profile_id,
                            payment_profile, 
                            payment,
                            authorize_API)
        token = self.env['payment.token'].create(token_vals)
        
        self.write({
            'token_id': token.id,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %s for partner with id %s", token.id, self.partner_id.id
        )
