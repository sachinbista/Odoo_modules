# -*- coding: utf-8 -*-

import pprint
import logging
from odoo import _, http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _partner_split_name(partner_name):
    if partner_name:
        return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


class EwayController(http.Controller):
    _return_url = '/payment/eway/return'
    _cancel_url = '/payment/eway/cancel'

    @http.route('/payment/eway/get_provider_info', type='json', auth='public', website=True)
    def eway_get_provider_info(self, **data):
        """ Return public information on the provider.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :return: Information on the provider, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """

        transaction = request.env['payment.transaction'].sudo().browse(data.get('paymentTransaction'))

        if not transaction:
            raise ValidationError(
                "Eway: " + _(
                    "No transaction found matching reference %s.", data.get('reference')
                )
            )
        
        encrypt_payload = {
            "Method": "eCrypt",
            "Items": [
                {
                    "Name": "card",
                    "Value": data.get('cardNumber')
                },
                {
                    "Name": "CVN",
                    "Value": data.get('cardCode')
                }
            ]
        }

        eway_encrypt_response = transaction.provider_id._eway_encrypt_credentials('/encrypt', payload=encrypt_payload)

        if eway_encrypt_response:
            if eway_encrypt_response.get('Method') != 1 and eway_encrypt_response.get('Errors') and not eway_encrypt_response.get('Items'):
                raise ValidationError(
                    "Eway: " + _(
                        "The Eway system shows:- %s.", transaction.provider_id.get_error_list(eway_encrypt_response.get('Errors'))
                    )
                )

        order = request.website.sale_get_order()
        if transaction:
            if data.get('cardNumber'):
                payload = {
                    "Customer": {
                        "Reference": data.get('reference'),
                        "FirstName": transaction.partner_id.name if not _partner_split_name(transaction.partner_id.name)[0] else
                        _partner_split_name(transaction.partner_id.name)[0],
                        "LastName": transaction.partner_id.name if not _partner_split_name(transaction.partner_id.name)[1] else
                        _partner_split_name(transaction.partner_id.name)[1],
                        "CompanyName": transaction.partner_id.company_name,
                        "Street1": transaction.partner_id.street,
                        "Street2": transaction.partner_id.street2,
                        "City": transaction.partner_id.city,
                        "State": transaction.partner_id.state_id.code,
                        "PostalCode": transaction.partner_id.zip,
                        "Country": transaction.partner_id.country_id.code,
                        "Phone": transaction.partner_id.phone,
                        "Email": transaction.partner_id.email,
                        "CardDetails": {
                            "Number": eway_encrypt_response.get("Items")[0].get("Value"),
                            "Name": data.get("nameOnCard"),
                            "ExpiryMonth": str(data.get('month')[:2]),
                            "ExpiryYear": str(data.get('year')[-2:]),
                            "CVN": eway_encrypt_response.get("Items")[1].get("Value"),
                        }
                    },
                    "Payment": {
                        "TotalAmount": int(float(transaction.amount) * 100),
                        "CurrencyCode": transaction.currency_id.name,
                    },
                    "Method": "ProcessPayment",
                    "TransactionType": "Purchase"
                }
            else:
                payload = {
                    "Customer": {
                        "Reference": data.get('reference'),
                        "FirstName": transaction.partner_id.name if not _partner_split_name(transaction.partner_id.name)[0] else
                        _partner_split_name(transaction.partner_id.name)[0],
                        "LastName": transaction.partner_id.name if not _partner_split_name(transaction.partner_id.name)[1] else
                        _partner_split_name(transaction.partner_id.name)[1],
                        "CompanyName": transaction.partner_id.company_name,
                        "Street1": transaction.partner_id.street,
                        "Street2": transaction.partner_id.street2,
                        "City": transaction.partner_id.city,
                        "State": transaction.partner_id.state_id.code,
                        "PostalCode": transaction.partner_id.zip,
                        "Country": transaction.partner_id.country_id.code,
                        "Phone": transaction.partner_id.phone,
                        "Email": transaction.partner_id.email,
                        "CardDetails": {
                            "Number": transaction.token_id.eway_card,
                            "Name": transaction.token_id.eway_card_name,
                            "ExpiryMonth": transaction.token_id.eway_expiry_month,
                            "ExpiryYear": transaction.token_id.eway_expiry_year,
                            "CVN": transaction.token_id.eway_cvn,
                        }
                    },
                    "Payment": {
                        "TotalAmount": int(float(transaction.amount) * 100),
                        "CurrencyCode": transaction.currency_id.name,
                    },
                    "Method": "ProcessPayment",
                    "TransactionType": "Purchase"
                }

        else:
            if data.get('cardNumber'):
                payload = {
                    "Customer": {
                        "Reference": data.get('reference'),
                        "FirstName": order.partner_id.name if not _partner_split_name(order.partner_id.name)[0] else
                        _partner_split_name(order.partner_id.name)[0],
                        "LastName": order.partner_id.name if not _partner_split_name(order.partner_id.name)[1] else
                        _partner_split_name(order.partner_id.name)[1],
                        "CompanyName": order.partner_id.company_name,
                        "Street1": order.partner_id.street,
                        "Street2": order.partner_id.street2,
                        "City": order.partner_id.city,
                        "State": order.partner_id.state_id.code,
                        "PostalCode": order.partner_id.zip,
                        "Country": order.partner_id.country_id.code,
                        "Phone": order.partner_id.phone,
                        "Email": order.partner_id.email,
                        "CardDetails": {
                            "Number": eway_encrypt_response.get("Items")[0].get("Value"),
                            "Name": data.get("nameOnCard"),
                            "ExpiryMonth": str(data.get('month')[:2]),
                            "ExpiryYear": str(data.get('year')[-2:]),
                            "CVN": eway_encrypt_response.get("Items")[1].get("Value"),
                        }
                    },
                    "Payment": {
                        "TotalAmount": int(float(order.amount_total) * 100),
                        "CurrencyCode": order.currency_id.name,
                    },
                    "Method": "ProcessPayment",
                    "TransactionType": "Purchase"
                }
            else:
                token = request.env['payment.token'].sudo().browse(data.get('token_id'))
                payload = {
                    "Customer": {
                        "Reference": data.get('reference'),
                        "FirstName": order.partner_id.name if not _partner_split_name(order.partner_id.name)[0] else
                        _partner_split_name(order.partner_id.name)[0],
                        "LastName": order.partner_id.name if not _partner_split_name(order.partner_id.name)[1] else
                        _partner_split_name(order.partner_id.name)[1],
                        "CompanyName": order.partner_id.company_name,
                        "Street1": order.partner_id.street,
                        "Street2": order.partner_id.street2,
                        "City": order.partner_id.city,
                        "State": order.partner_id.state_id.code,
                        "PostalCode": order.partner_id.zip,
                        "Country": order.partner_id.country_id.code,
                        "Phone": order.partner_id.phone,
                        "Email": order.partner_id.email,
                        "CardDetails": {
                            "Number": token.eway_card,
                            "Name": token.eway_card_name,
                            "ExpiryMonth": token.eway_expiry_month,
                            "ExpiryYear": token.eway_expiry_year,
                            "CVN": token.eway_cvn,
                        }
                    },
                    "Payment": {
                        "TotalAmount": int(float(order.amount_total) * 100),
                        "CurrencyCode": order.currency_id.name,
                    },
                    "Method": "ProcessPayment",
                    "TransactionType": "Purchase"
                }
        eway_response = transaction.provider_id._eway_make_request('/Transaction', payload=payload, method='POST')
        _logger.info("response from eway :- %s ", pprint.pformat(eway_response))

        if not eway_response.get('TransactionID') or not eway_response.get('TransactionStatus'):
            error_msg = ""

            if eway_response.get('Errors'):
                error_msg = ",  ".join(
                    [transaction.provider_id.get_error_list(error_msg) for error_msg in [code for code in eway_response.get('Errors').split(',')]])
            else:
                if eway_response.get('ResponseMessage'):
                    error_msg = ",  ".join(
                        [transaction.provider_id.get_error_list(error_msg) for error_msg in
                         [code for code in eway_response.get('ResponseMessage').split(',')]])
            raise ValidationError("Eway: " + _("%s") % (error_msg if error_msg else 'Something went Wrong!'))

            transaction._set_canceled()

            return request.redirect('/shop/cart')
        if data.get('cardNumber'):
            eway_response.update({
                'token_card_number':eway_encrypt_response.get("Items")[0].get("Value"),
                'token_card_cvn':eway_encrypt_response.get("Items")[1].get("Value"),
            }
            )
        transaction.sudo()._process_notification_data(eway_response)

        return request.redirect('/payment/status')

    @http.route([_return_url, _cancel_url], type='http', auth='public', csrf=False, website=True)
    def eway_return(self, **post):
        _logger.info('Data from the Payment eWAY as in the post %s', post)
        order = request.website.sale_get_order()
        _logger.info('After Payment eWAY form_feedback with post data %s', order)

        transaction = request.env['payment.transaction'].sudo().search([('eway_reference', '=', post.get('AccessCode'))])
        res_txt = transaction[0].provider_id._eway_make_request('/AccessCode/' + post.get('AccessCode'), method='GET')

        res_txt.update({'reference': transaction[0].reference})

        request.env['payment.transaction'].sudo()._handle_notification_data('eway', res_txt)

        return request.redirect('/payment/status')
