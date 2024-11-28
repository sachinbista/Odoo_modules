# -*- coding: utf-8 -*-

import pprint
import logging
from werkzeug import urls
from odoo import fields, _, models, api
from odoo.exceptions import ValidationError
from odoo.addons.odoo_pragmatic_payment_eway.controllers.main import EwayController
from odoo.addons.odoo_pragmatic_payment_eway import const

_logger = logging.getLogger(__name__)


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


class EWayPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    eway_reference = fields.Char("EWay Reference / AuthorisationCode",
                                 help="For storing either AccessCode from the response of '/AccessCodesShared' or \nAuthorisationCode from the response of '/Transaction'.")

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as provider-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """

        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'eway':
            return res

        processed_data = {
            'payment_transaction': self.id,
            'payment_flow': self.provider_id.eway_payment_method_type,
        }

        if self.provider_id.eway_payment_method_type == 'redirect_to_eway':
            checkout_session = self._eway_create_checkout_session()
            processed_data['code'] = checkout_session.get('AccessCode')
            processed_data['SharedPaymentUrl'] = checkout_session.get('SharedPaymentUrl')

        return processed_data

    def _eway_create_checkout_session(self):
        """ Create and return a Checkout Session.

        :return: The Checkout Session
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()

        data = {
            "Customer": {
                "Reference": self.reference,
                "FirstName": _partner_split_name(self.partner_id.name)[0],
                "LastName": _partner_split_name(self.partner_id.name)[1],
                "CompanyName": self.partner_id.company_name,
                "Street1": self.partner_id.street,
                "Street2": self.partner_id.street2,
                "City": self.partner_id.city,
                "State": self.partner_id.state_id.code,
                "PostalCode": self.partner_id.zip,
                "Country": self.partner_id.country_id.code,
                "Phone": self.partner_id.phone if self.partner_id.phone else self.partner_id.mobile,
                "Email": self.partner_id.email,
            },
            "Payment": {
                "TotalAmount": int(float(self.amount) * 100),
                "CurrencyCode": self.currency_id.name,
            },
            "RedirectUrl": urls.url_join(base_url, EwayController._return_url),
            "CancelUrl": urls.url_join(base_url, EwayController._cancel_url),
            "Method": "ProcessPayment" if not self.provider_id.capture_manually else "Authorise",
            "TransactionType": "Purchase",
        }

        checkout_session = self.provider_id._eway_make_request('/AccessCodesShared', payload=data, method='POST')

        if not checkout_session.get('AccessCode') or checkout_session.get('Errors'):
            raise ValidationError(
                "Eway: " + _(
                    "The Eway system shows:- %s.", self.provider_id.get_error_list(checkout_session.get('Errors'))
                )
            )

        self.eway_reference = checkout_session.get('AccessCode')

        return checkout_session

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Eway data.

        :param str provider: The provider of the provider that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'eway':
            return tx

        tx = self.search([('eway_reference', '=', notification_data.get('AccessCode')), ('provider_code', '=', 'eway')])

        if not tx:
            raise ValidationError(
                "Eway: " + _(
                    "No transaction found matching reference %s.", notification_data.get('reference')
                )
            )

        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Adyen data.

        Note: self.ensure_one()

        :param dict data: The feedback data build from information passed to the return route.
                          Depending on the operation of the transaction, the entries with the keys
                          'TransactionID' and 'ResponseMessage' can be
                          populated with their corresponding Eway API objects.
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'eway':
            return

        payment_method = self.env['payment.method']._get_from_code('card')
        payment_method_id = self.env['payment.method'].search([('code', '=', 'card')])
        self.payment_method_id = payment_method or payment_method_id or self.payment_method_id
        if self.tokenize:
            self._eway_tokenize_from_notification_data(notification_data)

        if not notification_data.get('TransactionID') or not notification_data.get('TransactionStatus'):
            _logger.exception(
                "Eway: Failed the Transaction. \nThe Eway system shows:- %s ",
                self.provider_id.get_response_code_details(notification_data.get('ResponseMessage'))
            )
            self._set_canceled()

        if notification_data.get('TransactionID') and 'successful' in self.provider_id.get_response_code_details(
                notification_data.get('ResponseMessage')).lower() and notification_data.get('TransactionStatus'):
            self.provider_reference = notification_data.get('TransactionID')
            if notification_data.get('AuthorisationCode'):
                self.eway_reference = notification_data.get('AuthorisationCode')
            _logger.info("Eway: Successfully completed the Transaction. \nThe Eway system shows:- %s ", notification_data)

            self._set_done()
        else:
            _logger.warning("Failed the Transaction \n Response: %s",
                            self.provider_id.get_response_code_details(notification_data.get('ResponseMessage')))
            self._set_error("Eway: " + _("Failed the Transaction \n Response: %s",
                                         self.provider_id.get_response_code_details(notification_data.get('ResponseMessage'))))

    def _send_refund_request(self, amount_to_refund=None, create_refund_transaction=True):
        """ Override of `payment` to send a refund request to Eway.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund.
        :param bool create_refund_transaction: Whether a refund transaction should be created
        :return: The refund transaction if any
        :rtype: recordset of `payment.transaction`
        """
        if self.provider_code != 'eway':
            return super()._send_refund_request(
                amount_to_refund=amount_to_refund,
                create_refund_transaction=create_refund_transaction,
            )
        refund_tx = super()._send_refund_request(
            amount_to_refund=amount_to_refund, create_refund_transaction=True
        )

        payload = {
            "Refund": {
                "TotalAmount": -refund_tx.amount
            }
        }

        _logger.info(
            "Payload of '/Transaction/<TransactionID>/Refund' request for transaction with reference %s:\n%s",
            refund_tx.provider_reference, pprint.pformat(payload)
        )

        response_content = refund_tx.provider_id._eway_make_request(f'Transaction/{refund_tx.provider_reference}/Refund', payload=payload,
                                                                    method='POST')
        _logger.info(
            "Response of '/Transaction/<TransactionID>/Refund' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(response_content)
        )
        response_content.update(entity_type='refund')

        refund_tx._handle_notification_data('eway', response_content)

        return refund_tx
    
    
    def _eway_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        :param dict notification_data: The notification data built with Stripe objects.
                                       See `_process_notification_data`.
        :return: None
        """
        payment_method = self.env['payment.method']._get_from_code('card')
        payment_method_id = self.env['payment.method'].search([('code', '=', 'card')])
        self.payment_method_id = payment_method or payment_method_id or self.payment_method_id
        if not payment_method:
            _logger.warning(
                "requested tokenization from notification data with missing payment method"
            )
            return
        # Extract the Stripe objects from the notification data.
        # if self.eway_payment_method_type == 'from_odoo':
        # Another payment method (e.g., SEPA) might have been generated.
        

            # Create the token.
        if self.provider_id.eway_payment_method_type == 'from_odoo':
            token = self.env['payment.token'].create({
                'provider_id': self.provider_id.id,
                'payment_method_id': self.payment_method_id.id,
                'payment_details': notification_data.get('Customer').get('CardDetails').get('Number')[-4:],
                'partner_id': self.partner_id.id,
                'provider_ref': '',
                'eway_card':notification_data.get('token_card_number'),
                'eway_cvn':notification_data.get('token_card_cvn'),
                'eway_expiry_month':notification_data.get('Customer').get('CardDetails').get('ExpiryMonth'),
                'eway_expiry_year':notification_data.get('Customer').get('CardDetails').get('ExpiryYear'),
                'eway_card_name':notification_data.get('Customer').get('CardDetails').get('Name')
                
            })
            self.write({
                'token_id': token,
                'tokenize': False,
            })
            _logger.info(
                "created token with id %(token_id)s for partner with id %(partner_id)s from "
                "transaction with reference %(ref)s",
                {
                    'token_id': token.id,
                    'partner_id': self.partner_id.id,
                    'ref': self.reference,
                },
            )


class EWayPaymentToken(models.Model):
    _inherit = 'payment.token'

    token_eway = fields.Char(string="Token")
    eway_response_message = fields.Text(string="EWay Error Message")
    eway_card = fields.Char(string="Card")
    eway_cvn = fields.Char(string="cvv")
    eway_expiry_month = fields.Char(string="expiry month")
    eway_expiry_year = fields.Char(string="expiry year")
    eway_card_name = fields.Char(string="card name")

