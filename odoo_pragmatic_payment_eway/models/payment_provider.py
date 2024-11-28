# -*- coding: utf-8 -*-

import json
import logging
import requests
from werkzeug import urls
from odoo import _, models, fields
from odoo.addons.odoo_pragmatic_payment_eway import const
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EWayPaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('eway', "eWAY")], ondelete={'eway': 'set default'})

    eway_api_key = fields.Char(string="API Key", required_if_provider='eway')
    eway_password = fields.Char(string="Password", required_if_provider='eway')
    eway_public_api_key = fields.Char(string="Public API Key", required_if_provider='eway')

    eway_payment_method_type = fields.Selection(
        selection=[('from_odoo', "Payment From Odoo"), ('redirect_to_eway', "Redirect to Eway Page")],
        string="Payments Through", default='redirect_to_eway', required_if_provider='eway',
        help="Determines with what payment method the customer can pay, either it is from odoo from or direct to eway"
    )

    def _get_eway_api_url(self):
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://api.ewaypayments.com'
        else:
            return 'https://api.sandbox.ewaypayments.com'

    def _eway_encrypt_credentials(self, endpoint, payload=None):
        self.ensure_one()
        eway_url = urls.url_join(self._get_eway_api_url(), endpoint)

        headers = {
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(eway_url, headers=headers, data=json.dumps(payload),
                                     auth=(self.eway_public_api_key, self.eway_password))
            if response.status_code != 200:
                raise ValidationError(
                    "Eway: " + _(
                        "The communication with the API failed.\n Please check your Eway Credentials"
                    )
                )
        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", eway_url)
            raise ValidationError(
                "Eway: " + _(
                    "Could not establish the connection to the API. Please check your Internet Connection"
                )
            )

        return response.json()

    def _eway_make_request(self, endpoint, payload=None, method='POST', offline=False):
        self.ensure_one()
        eway_url = urls.url_join(self._get_eway_api_url(), endpoint)

        headers = {
            'Content-Type': 'application/json',
        }

        try:
            if method == 'POST':
                response = requests.post(eway_url, headers=headers, data=json.dumps(payload),
                                         auth=(self.eway_api_key, self.eway_password))
            elif method == 'GET':
                response = requests.get(eway_url, auth=(self.eway_api_key, self.eway_password))
            else:
                _logger.exception("Nothing for process")
            if response.status_code != 200 and not offline:
                raise ValidationError(
                    "Eway: " + _(
                        "The communication with the API failed.\n Please check your Eway Credentials"
                    )
                )

        except requests.exceptions.ConnectionError:
            _logger.exception("unable to reach endpoint at %s", eway_url)
            raise ValidationError(
                "Eway: " + _(
                    "Could not establish the connection to the API. Please check your Internet Connection"
                )
            )

        return response.json()

    def get_error_list(self, code):
        if code:
            error_list = {
                'V6000': 'Validation error',
                'V6001': 'Invalid CustomerIP',
                'V6002': 'Invalid DeviceID',
                'V6003': 'Invalid Request PartnerID',
                'V6004': 'Invalid Request Method',
                'V6010': 'Invalid TransactionType, account not certified for eCome only MOTO or Recurring available',
                'V6011': 'Invalid Payment TotalAmount',
                'V6012': 'Invalid Payment InvoiceDescription',
                'V6013': 'Invalid Payment InvoiceNumber',
                'V6014': 'Invalid Payment InvoiceReference',
                'V6015': 'Invalid Payment CurrencyCode',
                'V6016': 'Payment Required',
                'V6017': 'Payment CurrencyCode Required',
                'V6018': 'Unknown Payment CurrencyCode',
                'V6019': 'Cardholder identity authentication required',
                'V6020': 'Cardholder Input Required',
                'V6021': 'EWAY_CARDHOLDERNAME Required',
                'V6022': 'EWAY_CARDNUMBER Required',
                'V6023': 'EWAY_CARDCVN Required',
                'V6024': 'Cardholder Identity Authentication One Time Password Not Active Yet',
                'V6025': 'PIN Required',
                'V6033': 'Invalid Expiry Date',
                'V6034': 'Invalid Issue Number',
                'V6035': 'Invalid Valid From Date',
                'V6039': 'Invalid Network Token Status',
                'V6040': 'Invalid TokenCustomerID',
                'V6041': 'Customer Required',
                'V6042': 'Customer FirstName Required',
                'V6043': 'Customer LastName Required',
                'V6044': 'Customer CountryCode Required',
                'V6045': 'Customer Title Required',
                'V6046': 'TokenCustomerID Required',
                'V6047': 'RedirectURL Required',
                'V6048': 'CheckoutURL Required when CheckoutPayment specified',
                'V6049': 'Invalid Checkout URL',
                'V6051': 'Invalid Customer FirstName',
                'V6052': 'Invalid Customer LastName',
                'V6053': 'Invalid Customer CountryCode',
                'V6058': 'Invalid Customer Title',
                'V6059': 'Invalid RedirectURL',
                'V6060': 'Invalid TokenCustomerID',
                'V6061': 'Invalid Customer Reference',
                'V6062': 'Invalid Customer CompanyName',
                'V6063': 'Invalid Customer JobDescription',
                'V6064': 'Invalid Customer Street1',
                'V6065': 'Invalid Customer Street2',
                'V6066': 'Invalid Customer City',
                'V6067': 'Invalid Customer State',
                'V6068': 'Invalid Customer PostalCode',
                'V6069': 'Invalid Customer Email',
                'V6070': 'Invalid Customer Phone',
                'V6071': 'Invalid Customer Mobile',
                'V6072': 'Invalid Customer Comments',
                'V6073': 'Invalid Customer Fax',
                'V6074': 'Invalid Customer URL',
                'V6075': 'Invalid ShippingAddress FirstName',
                'V6076': 'Invalid ShippingAddress LastName',
                'V6077': 'Invalid ShippingAddress Street1',
                'V6078': 'Invalid ShippingAddress Street2',
                'V6079': 'Invalid ShippingAddress City',
                'V6080': 'Invalid ShippingAddress State',
                'V6081': 'Invalid ShippingAddress PostalCode',
                'V6082': 'Invalid ShippingAddress Email',
                'V6083': 'Invalid ShippingAddress Phone',
                'V6084': 'Invalid ShippingAddress Country',
                'V6085': 'Invalid ShippingAddress ShippingMethod',
                'V6086': 'Invalid ShippingAddress Fax',
                'V6091': 'Unknown Customer CountryCode',
                'V6092': 'Unknown ShippingAddress CountryCode',
                'V6093': 'Insufficient Address Information',
                'V6100': 'Invalid EWAY_CARDNAME',
                'V6101': 'Invalid EWAY_CARDEXPIRYMONTH',
                'V6102': 'Invalid EWAY_CARDEXPIRYYEAR',
                'V6103': 'Invalid EWAY_CARDSTARTMONTH',
                'V6104': 'Invalid EWAY_CARDSTARTYEAR',
                'V6105': 'Invalid EWAY_CARDISSUENUMBER',
                'V6106': 'Invalid EWAY_CARDCVN',
                'V6107': 'Invalid EWAY_ACCESSCODE',
                'V6108': 'Invalid CustomerHostAddress',
                'V6109': 'Invalid UserAgent',
                'V6110': 'Invalid EWAY_CARDNUMBER',
                'V6111': 'Unauthorised API Access, Account Not PCI Certified',
                'V6112': 'Redundant card details other than expiry year and month',
                'V6113': 'Invalid transaction for refund',
                'V6114': 'Gateway validation error',
                'V6115': 'Invalid DirectRefundRequest, Transaction ID',
                'V6116': 'Invalid card data on original TransactionID',
                'V6117': 'Invalid CreateAccessCodeSharedRequest, FooterText',
                'V6118': 'Invalid CreateAccessCodeSharedRequest, HeaderText',
                'V6119': 'Invalid CreateAccessCodeSharedRequest, Language',
                'V6120': 'Invalid CreateAccessCodeSharedRequest, LogoUrl',
                'V6121': 'Invalid TransactionSearch, Filter Match Type',
                'V6122': 'Invalid TransactionSearch, Non numeric Transaction ID',
                'V6123': 'Invalid TransactionSearch,no TransactionID or AccessCode specified',
                'V6124': 'Invalid Line Items. The line items have been provided however the totals do not match the TotalAmount field',
                'V6125': 'Selected Payment Type not enabled',
                'V6126': 'Invalid encrypted card number, decryption failed',
                'V6127': 'Invalid encrypted cvn, decryption failed',
                'V6128': 'Invalid Method for Payment Type',
                'V6129': 'Transaction has not been authorised for Capture/Cancellation',
                'V6130': 'Generic customer information error',
                'V6131': 'Generic shipping information error',
                'V6132': 'Transaction has already been completed or voided, operation not permitted',
                'V6133': 'Checkout not available for Payment Type',
                'V6134': 'Invalid Auth Transaction ID for Capture/Void',
                'V6135': 'PayPal Error Processing Refund',
                'V6136': 'Original transaction does not exist or state is incorrect',
                'V6140': 'Merchant account is suspended',
                'V6141': 'Invalid PayPal account details or API signature',
                'V6142': 'Authorise not available for Bank/Branch',
                'V6143': 'Invalid Public Key',
                'V6144': 'Method not available with Public API Key Authentication',
                'V6145': 'Credit Card not allow if Token Customer ID is provided with Public API Key Authentication',
                'V6146': 'Client Side Encryption Key Missing or Invalid',
                'V6147': 'Unable to Create One Time Code for Secure Field',
                'V6148': 'Secure Field has Expired',
                'V6149': 'Invalid Secure Field One Time Code',
                'V6150': 'Invalid Refund Amount',
                'V6151': 'Refund amount greater than original transaction',
                'V6152': 'Original transaction already refunded for total amount',
                'V6153': 'Card type not support by merchant',
                'V6154': 'Insufficient Funds Available For Refund',
                'V6155': 'Missing one or more fields in request',
                'V6160': 'Encryption Method Not Supported',
                'V6161': 'Encryption failed, missing or invalid key',
                'V6165': 'Invalid Click-to-Pay (Visa Checkout) data or decryption failed',
                'V6170': 'Invalid TransactionSearch, Invoice Number is not unique',
                'V6171': 'Invalid TransactionSearch, Invoice Number not found',
                'V6220': 'Three domain secure XID invalid',
                'V6221': 'Three domain secure ECI invalid',
                'V6222': 'Three domain secure AVV invalid',
                'V6223': 'Three domain secure XID is required',
                'V6224': 'Three Domain Secure ECI is required',
                'V6225': 'Three Domain Secure AVV is required',
                'V6226': 'Three Domain Secure AuthStatus is required',
                'V6227': 'Three Domain Secure AuthStatus invalid',
                'V6228': 'Three domain secure Version is required',
                'V6230': 'Three domain secure Directory Server Txn ID invalid',
                'V6231': 'Three domain secure Directory Server Txn ID is required',
                'V6232': 'Three domain secure Version is invalid',
                'V6501': 'Invalid Amex InstallmentPlan',
                'V6502': 'Invalid Number Of Installments for Amex. Valid values are from 0 to 99 inclusive',
                'V6503': 'Merchant Amex ID required',
                'V6504': 'Invalid Merchant Amex ID',
                'V6505': 'Merchant Terminal ID required',
                'V6506': 'Merchant category code required',
                'V6507': 'Invalid merchant category code',
                'V6508': 'Amex 3D ECI required',
                'V6509': 'Invalid Amex 3D ECI',
                'V6510': 'Invalid Amex 3D verification value',
                'V6511': 'Invalid merchant location data',
                'V6512': 'Invalid merchant street address',
                'V6513': 'Invalid merchant city',
                'V6514': 'Invalid merchant country',
                'V6515': 'Invalid merchant phone',
                'V6516': 'Invalid merchant postcode',
                'V6517': 'Amex connection error',
                'V6518': 'Amex EC Card Details API returned invalid data',
                'V6520': 'Invalid or missing Amex Point Of Sale Data',
                'V6521': 'Invalid or missing Amex transaction date time',
                'V6522': 'Invalid or missing Amex Original transaction date time',
                'V6530': 'Credit Card Number in non Credit Card Field',
                'D4401': 'Failed: Refer to Issuer',
                'D4402': 'Failed: Refer to Issuer, special',
                'D4403': 'Failed: No Merchant',
                'D4404': 'Failed: Pick Up Card',
                'D4405': 'Failed: Do Not Honour',
                'D4406': 'Failed: Error',
                'D4407': 'Failed: Pick Up Card, Special',
                'D4409': 'Failed: Request In Progress',
                'D4412': 'Failed: Invalid Transaction',
                'D4413': 'Failed: Invalid Amount',
                'D4414': 'Failed: Invalid Card Number',
                'D4415': 'Failed: No Issuer',
                'D4417': 'Failed: 3D Secure Error',
                'D4419': 'Failed: Re-enter Last Transaction',
                'D4421': 'Failed: No Action Taken',
                'D4422': 'Failed: Suspected Malfunction',
                'D4423': 'Failed: Unacceptable Transaction Fee',
                'D4425': 'Failed: Unable to Locate Record On File',
                'D4430': 'Failed: Format Error',
                'D4431': 'Failed: Bank Not Supported By Switch',
                'D4433': 'Failed: Expired Card, Capture',
                'D4434': 'Failed: Suspected Fraud, Retain Card',
                'D4435': 'Failed: Card Acceptor, Contact Acquirer, Retain Card',
                'D4436': 'Failed: Restricted Card, Retain Card',
                'D4437': 'Failed: Contact Acquirer Security Department, Retain Card',
                'D4438': 'Failed: PIN Tries Exceeded, Capture',
                'D4439': 'Failed: No Credit Account',
                'D4440': 'Failed: Function Not Supported',
                'D4441': 'Failed: Lost Card',
                'D4442': 'Failed: No Universal Account',
                'D4443': 'Failed: Stolen Card',
                'D4444': 'Failed: No Investment Account',
                'D4450': 'Failed: Click-to-Pay (Visa Checkout) Transaction Error',
                'D4451': 'Failed: Insufficient Funds',
                'D4452': 'Failed: No Cheque Account',
                'D4453': 'Failed: No Savings Account',
                'D4454': 'Failed: Expired Card',
                'D4455': 'Failed: Incorrect PIN',
                'D4456': 'Failed: No Card Record',
                'D4457': 'Failed: Function Not Permitted to Cardholder',
                'D4458': 'Failed: Function Not Permitted to Terminal',
                'D4459': 'Failed: Suspected Fraud',
                'D4460': 'Failed: Acceptor Contact Acquirer',
                'D4461': 'Failed: Exceeds Withdrawal Limit',
                'D4462': 'Failed: Restricted Card',
                'D4463': 'Failed: Security Violation',
                'D4464': 'Failed: Original Amount Incorrect',
                'D4466': 'Failed: Acceptor Contact Acquirer, Security',
                'D4467': 'Failed: Capture Card',
                'D4475': 'Failed: PIN Tries Exceeded',
                'D4476': 'Failed: Invalidate Txn Reference',
                'D4481': 'Failed: Accumulated Transaction Counter (Amount) Exceeded',
                'D4482': 'Failed: CVV Validation Error',
                'D4483': 'Failed: Acquirer Is Not Accepting Transactions From You At This Time',
                'D4484': 'Failed: Acquirer Is Not Accepting This Transaction',
                'D4490': 'Failed: Cut off In Progress',
                'D4491': 'Failed: Card Issuer Unavailable',
                'D4492': 'Failed: Unable To Route Transaction',
                'D4493': 'Failed: Cannot Complete, Violation Of The Law',
                'D4494': 'Failed: Duplicate Transaction',
                'D4495': 'Failed: Amex Declined',
                'D4496': 'Failed: System Error',
                'D4497': 'Failed: MasterPass Error',
                'D4498': 'Failed: PayPal Create Transaction Error',
                'D4499': 'Failed: Invalid Transaction for Auth/Void',
            }

            if error_list.get(code):
                return error_list.get(code)

    def get_response_code_details(self, code):
        """
            Mostly this method is triggered from the response error code, when the payment is redirecting to Eway page
            Here we added an extra word either it is 'Successful' or 'Failed' in the pre section of each value, actually these words are not in the eway API docs
            These static words for understanding if the response status either success or fail in the processing time
            :param code: this is a key, that we got from the API response (response.get('ResponseMessage'))
            :return: this will return a message according to the code that got from the API response if the code is in the dict 'response_code_list', else
            It will return one static fail message at the end of the function
            :rtype: string
        """
        if code:
            response_code_list = {
                'A2000': 'Successful: Transaction Approved',
                'A2008': 'Successful: Honour With Identification',
                'A2010': 'Successful: Approved For Partial Amount',
                'A2011': 'Successful: Approved, VIP',
                'A2016': 'Successful: Approved, Update Track 3',
                'D4401': 'Failed: Refer to Issuer',
                'D4402': 'Failed: Refer to Issuer, special',
                'D4403': 'Failed: No Merchant',
                'D4404': 'Failed: Pick Up Card',
                'D4405': 'Failed: Do Not Honour',
                'D4406': 'Failed: Error',
                'D4407': 'Failed: Pick Up Card, Special',
                'D4409': 'Failed: Request In Progress',
                'D4412': 'Failed: Invalid Transaction',
                'D4413': 'Failed: Invalid Amount',
                'D4414': 'Failed: Invalid Card Number',
                'D4415': 'Failed: No Issuer',
                'D4417': 'Failed: 3D Secure Error',
                'D4419': 'Failed: Re-enter Last Transaction',
                'D4421': 'Failed: No Action Taken',
                'D4422': 'Failed: Suspected Malfunction',
                'D4423': 'Failed: Unacceptable Transaction Fee',
                'D4425': 'Failed: Unable to Locate Record On File',
                'D4430': 'Failed: Format Error',
                'D4431': 'Failed: Bank Not Supported By Switch',
                'D4433': 'Failed: Expired Card, Capture',
                'D4434': 'Failed: Suspected Fraud, Retain Card',
                'D4435': 'Failed: Card Acceptor, Contact Acquirer, Retain Card',
                'D4436': 'Failed: Restricted Card, Retain Card',
                'D4437': 'Failed: Contact Acquirer Security Department, Retain Card',
                'D4438': 'Failed: PIN Tries Exceeded, Capture',
                'D4439': 'Failed: No Credit Account',
                'D4440': 'Failed: Function Not Supported',
                'D4441': 'Failed: Lost Card',
                'D4442': 'Failed: No Universal Account',
                'D4443': 'Failed: Stolen Card',
                'D4444': 'Failed: No Investment Account',
                'D4450': 'Failed: Click-to-Pay (Visa Checkout) Transaction Error',
                'D4451': 'Failed: Insufficient Funds',
                'D4452': 'Failed: No Cheque Account',
                'D4453': 'Failed: No Savings Account',
                'D4454': 'Failed: Expired Card',
                'D4455': 'Failed: Incorrect PIN',
                'D4456': 'Failed: No Card Record',
                'D4457': 'Failed: Function Not Permitted to Cardholder',
                'D4458': 'Failed: Function Not Permitted to Terminal',
                'D4459': 'Failed: Suspected Fraud',
                'D4460': 'Failed: Acceptor Contact Acquirer',
                'D4461': 'Failed: Exceeds Withdrawal Limit',
                'D4462': 'Failed: Restricted Card',
                'D4463': 'Failed: Security Violation',
                'D4464': 'Failed: Original Amount Incorrect',
                'D4466': 'Failed: Acceptor Contact Acquirer, Security',
                'D4467': 'Failed: Capture Card',
                'D4475': 'Failed: PIN Tries Exceeded',
                'D4476': 'Failed: Invalidate Txn Reference',
                'D4481': 'Failed: Accumulated Transaction Counter (Amount) Exceeded',
                'D4482': 'Failed: CVV Validation Error',
                'D4483': 'Failed: Acquirer Is Not Accepting Transactions From You At This Time',
                'D4484': 'Failed: Acquirer Is Not Accepting This Transaction',
                'D4490': 'Failed: Cut off In Progress',
                'D4491': 'Failed: Card Issuer Unavailable',
                'D4492': 'Failed: Unable To Route Transaction',
                'D4493': 'Failed: Cannot Complete, Violation Of The Law',
                'D4494': 'Failed: Duplicate Transaction',
                'D4495': 'Failed: Amex Declined',
                'D4496': 'Failed: System Error',
                'D4497': 'Failed: MasterPass Error',
                'D4498': 'Failed: PayPal Create Transaction Error',
                'D4499': 'Failed: Invalid Transaction for Auth/Void',
            }

            if response_code_list.get(code):
                return response_code_list.get(code)

            return "Failed: Something went Wrong!."

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'eway':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES

    def _get_validation_amount(self):
        """ Override of payment to return the amount for Authorize.Net validation operations.

        :return: The validation amount
        :rtype: float
        """
        res = super()._get_validation_amount()
        if self.code != 'eway':
            return res

        return 0.01
