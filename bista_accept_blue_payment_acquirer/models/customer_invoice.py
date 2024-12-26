from odoo import api, fields, models,_
import requests
import json
from requests.auth import HTTPBasicAuth
from odoo.exceptions import ValidationError

import re

AMEX_CC_RE = re.compile(r"^3[47][0-9]{13}$")
VISA_CC_RE = re.compile(r"^4[0-9]{12}(?:[0-9]{3})?$")
MASTERCARD_CC_RE = re.compile(r"^5[1-5][0-9]{14}$")
DISCOVER_CC_RE = re.compile(r"^6(?:011|5[0-9]{2})[0-9]{12}$")
DINERS_CLUB_CC_RE = re.compile(r"^3(?:0[0-5]|[68][0-9])[0-9]{11}$")
JCB_CC_RE = re.compile(r"^(?:2131|1800|3[0-9]\d{3})\d{11}$")
union_CC_RE = re.compile(r"^(62[0-9]{14,17})$")



CC_MAP = {"americanexpress": AMEX_CC_RE, "visa": VISA_CC_RE,
          "mastercard": MASTERCARD_CC_RE, "discover": DISCOVER_CC_RE,
          "dinersclub": DINERS_CLUB_CC_RE, "jcb": JCB_CC_RE,"union":union_CC_RE}


def cc_type(cc_number):
    for type, regexp in CC_MAP.items():
        if regexp.match(str(cc_number)):
            return type
    return None



class AccountPaymentRegister(models.TransientModel):
    _inherit='account.payment.register'


    credit_card_details=fields.Many2one('card.details',string="Pay with existing card.." , domain="[('partner_id', '=',parent_partner_id),('access_token', '!=',False)]")
    pay_new_card=fields.Boolean('Pay with new card')
    credit_card_no = fields.Char('Card Number', size=16)
    credit_card_code = fields.Char('CVV', size=4)
    credit_card_type = fields.Selection([
        ('americanexpress', 'American Express'),
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('discover', 'Discover'),
        ('dinersclub', 'Diners Club'),
        ('union', 'Union'),
        ('jcb', 'JCB')], 'Card Type')

    credit_card_expiration_month = fields.Selection([('01', '01'), ('02', '02'), ('03', '03'), ('04', '04'),
                                                     ('05', '05'), ('06', '06'), ('07', '07'), ('08', '08'),
                                                     ('09', '09'), ('10', '10'), ('11', '11'), ('12', '12'),
                                                     ], 'Expires Month')
    credit_card_expiration_year = fields.Char('Expires Year', size=2)
    store_card=fields.Boolean('Save card')
    accept_blue_reference_no=fields.Many2one('accept.blue.line',string="Refund Invoice Reference No")
    origin_inv_id=fields.Many2one('account.move')
    refund_amount=fields.Float('Refund Amount')
    is_accept_blue=fields.Boolean('Is accept blue',related='payment_method_line_id.is_accept_blue_payment')
    is_direct_credit_note=fields.Boolean('Is direct credit note')
    parent_partner_id=fields.Many2one('res.partner')
    in_invoice_id=fields.Many2many('account.move')


    @api.onchange('credit_card_no')
    def _onchange_card_no(self):
        for line in self:
            if line.credit_card_no:
                card_type =cc_type(line.credit_card_no)
                if card_type:
                    line.credit_card_type = card_type


    @api.onchange('pay_new_card')
    def _onchange_pay_new_card(self):
        for line in self:
            if line.pay_new_card:
                line.credit_card_details = False

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentRegister, self).default_get(fields)
        inv_cus_ids = self.env['account.move'].browse(self.env.context.get('active_ids')).mapped('partner_id')
        if len(inv_cus_ids)>1:
            res.update({'in_invoice_id': [ (6, 0, self.env['account.move'].browse(self.env.context.get('active_ids')).ids)]})

        else:
            reverse_move_id=self.env['account.move'].browse(self.env.context.get('active_ids'))
            if reverse_move_id:
                if not reverse_move_id.partner_id.parent_id:
                    parent_partner_id=reverse_move_id.partner_id.id
                elif reverse_move_id.partner_id.parent_id:
                    parent_partner_id = reverse_move_id.partner_id.parent_id.id
                else:
                    parent_partner_id=False
                res.update({'origin_inv_id':reverse_move_id.reversed_entry_id.id,'parent_partner_id':parent_partner_id,'in_invoice_id':[(6,0,self.env['account.move'].browse(self.env.context.get('active_ids')).ids)]})
            if not reverse_move_id[0].reversed_entry_id and  reverse_move_id[0].move_type in ('in_refund','in_invoice'):
                res.update({'is_direct_credit_note': True})
        return res

    @api.onchange('accept_blue_reference_no','journal_id')
    def _onchange_accept_blue_reference_no(self):
        acc_blu_line=[]
        for line in self:
            if line.accept_blue_reference_no:
                if line.accept_blue_reference_no.pay_status != 'settled':
                    raise ValidationError(_("The transaction is not yet settled so it cannot yet be refunded."))
                self.refund_amount=line.accept_blue_reference_no.refund_amount
            accept_blue_line=self.env['accept.blue.line'].search([('account_accept_move_id','=',self.origin_inv_id.id)])
            for rec in accept_blue_line:
                if rec.refund_amount > 0:
                    acc_blu_line.append(rec.id)
        return {'domain': {'accept_blue_reference_no': [('id', 'in', acc_blu_line)]}}

    def store_credit_card_details(self):
        partner_card_details_id=self.env['card.details'].create({
            'credit_card_type':self.credit_card_type,
            'credit_card_no':self.credit_card_no,
            'credit_card_code':self.credit_card_code,
            'credit_card_expiration_month':self.credit_card_expiration_month,
            'credit_card_expiration_year':self.credit_card_expiration_year,
            'partner_id':self.partner_id.id
        })
        return partner_card_details_id

    def get_customer_rec(self, config_id, move_id):
        if config_id:
            sale_order_id = self.env['sale.order'].search([('name', '=', move_id.invoice_origin)])
            if sale_order_id:
                acce_blue_cust_id=sale_order_id.partner_id.accept_blue_creeate_cus_id
            else:
                acce_blue_cust_id=move_id.partner_id.accept_blue_creeate_cus_id
            url = config_id.api_url + 'customers/' + str(acce_blue_cust_id)
            resp = requests.get(url, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
            if resp.status_code == 200:
                rec = json.loads(resp.text)
                return rec.get('id')





    def create_customer_rec(self,config_id,move_id):
        if move_id.invoice_origin:
            sale_order_id=self.env['sale.order'].search([('name','=',move_id.invoice_origin)])
            if sale_order_id:
                email=sale_order_id.partner_id.email
                phone= sale_order_id.partner_id.phone
                identifier=sale_order_id.partner_id.name
                first_name=sale_order_id.partner_id.name
            else:
                email = move_id.partner_id.email
                phone = move_id.partner_id.phone
                identifier = move_id.partner_id.name
                first_name = move_id.partner_id.name
        else:
            email = move_id.partner_id.email
            phone = move_id.partner_id.phone
            identifier = move_id.partner_id.name
            first_name = move_id.partner_id.name
        error_msg=''
        if config_id:
            url = config_id.api_url + 'customers'
            data = {
                'identifier': identifier,
                'first_name': first_name,
                'email': email,
                'phone':phone,
            }

            resp = requests.post(url, json=data, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
            if resp.status_code == 201:
                rec=json.loads(resp.text)
                return rec.get('id')
            else:
                error = json.loads(resp.text)
                if 'error_details' in error:
                    error_details = error.get('error_details')
                    if 'email' in error_details:
                        error_msg += 'email' + ' ' + error_details.get('email')[0] + ' ,'
                    if 'phone' in error_details:
                        error_msg += 'phone' + ' ' + error_details.get('phone')[0]
                    raise ValidationError(_(error_msg + 'On Customer'))

    def _accept_blue_transaction_not_group_payment(self, config_id, payments):
        error_msg = ''
        created_id = ''
        credit_card_no = ''
        if self.payment_method_line_id.is_accept_blue_payment:
            if config_id:
                if not self.origin_inv_id and not self.is_direct_credit_note:
                    move_id=self.env['account.move'].search([('name','=',payments.ref)])
                    # move_id = self.in_invoice_id
                    if move_id:
                        sale_order_id = self.env['sale.order'].search([('name', '=', move_id.invoice_origin)])
                        if sale_order_id:
                            created_cus_accept_blue_id = sale_order_id.partner_id.accept_blue_creeate_cus_id
                        else:
                            created_cus_accept_blue_id = move_id.partner_id.accept_blue_creeate_cus_id
                        if created_cus_accept_blue_id:
                            exist_cus_id = self.get_customer_rec(config_id, move_id)
                            if exist_cus_id == created_cus_accept_blue_id:
                                created_id = created_cus_accept_blue_id
                            else:
                                created_id = self.create_customer_rec(config_id, move_id)
                                if created_id:
                                    sale_order_id.partner_id.accept_blue_creeate_cus_id = created_id
                                    created_id = created_id
                                else:
                                    created_id = ''
                        else:
                            created_id = self.create_customer_rec(config_id, move_id)
                            if created_id:
                                sale_order_id.partner_id.accept_blue_creeate_cus_id = created_id
                                created_id = created_id
                            else:
                                created_id = ''
                    # account_move_id=self.env['account.move'].search([('name','=',self.communication)])
                        # if self.amount > account_move_id.amount_residual:
                        #     raise ValidationError(_('You can not change original amount'))
                    if not self.credit_card_details and not self.pay_new_card:
                        raise ValidationError(_("Please select Card Details For Payments.."))
                    transaction_url = config_id.api_url + 'transactions/charge'
                    if not self.pay_new_card:
                        if self.credit_card_details:
                            if self.credit_card_details.credit_card_expiration_year.isdigit():
                                expiry_year = int('20' + self.credit_card_details.credit_card_expiration_year)
                            else:
                                raise ValidationError(_('Please Put Valid Expiry year'))
                            data = {
                                'amount': payments.amount,
                                'expiry_month': int(self.credit_card_details.credit_card_expiration_month),
                                'expiry_year': expiry_year,
                                'cvv2': self.credit_card_details.credit_card_code,
                                'source': 'tkn-' + self.credit_card_details.access_token,
                                "customer": {
                                    "customer_id": created_id
                                },
                                "transaction_details": {
                                    "invoice_number": move_id.name if move_id else False
                                }
                            }
                            credit_card_no=self.credit_card_details.card_no

                    elif self.pay_new_card and self.store_card:
                        card_details = self.store_credit_card_details()
                        if self.credit_card_expiration_year.isdigit():
                            expiry_year = int('20' + self.credit_card_expiration_year)
                        else:
                            raise ValidationError(_('Please Put Valid Expiry year'))
                        if card_details:
                            data = {
                                'amount': payments.amount,
                                'expiry_month': int(self.credit_card_expiration_month),
                                'expiry_year': expiry_year,
                                'cvv2': card_details.credit_card_code,
                                'source': 'tkn-' + card_details.access_token,

                                "customer": {
                                    "customer_id": created_id
                                },
                                "transaction_details": {
                                    "invoice_number": move_id.name if move_id else False
                                }
                            }
                            credit_card_no = card_details.credit_card_no

                    elif self.pay_new_card and not self.store_card:
                        if self.credit_card_expiration_year.isdigit():
                            expiry_year = int('20' + self.credit_card_expiration_year)
                        else:
                            raise ValidationError(_('Please Put Valid Expiry year'))
                        expiry_month = int(self.credit_card_expiration_month)
                        data = {
                            'expiry_month': expiry_month,
                            'expiry_year': expiry_year,
                            'card': self.credit_card_no,
                            "cvv2": self.credit_card_code,
                            'save_card': True
                        }

                        url = config_id.api_url + 'transactions/verify'
                        resp = requests.post(url, json=data,
                                             auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                        res_text = json.loads(resp.text)
                        error = json.loads(resp.text)
                        if resp.status_code == 200:
                            if res_text.get('status_code') == 'A':
                                data = {
                                    'amount': payments.amount,
                                    'expiry_month': int(self.credit_card_expiration_month),
                                    'expiry_year': expiry_year,
                                    'cvv2': self.credit_card_code,
                                    'source': 'tkn-' + res_text.get('card_ref'),

                                    "customer": {
                                        "customer_id": created_id
                                    },
                                    "transaction_details": {
                                        "invoice_number": move_id.name if move_id else False
                                    }
                                }
                                lst_4_digi = self.credit_card_no[-4:].rjust(len(self.credit_card_no), '*')
                                credit_card_no = lst_4_digi
                            else:
                                if 'error_details' in error:
                                    error_details = error.get('error_details')
                                    if 'card' in error_details:
                                        error_msg += 'Card' + ' ' + error_details.get('card')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                    if 'expiry_month' in error_details:
                                        error_msg += 'Expiry Month' + ' ' + error_details.get('expiry_month')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                    if 'expiry_year' in error_details:
                                        error_msg += 'Expiry Year' + ' ' + error_details.get('expiry_year')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                    if 'cvv2' in error_details:
                                        error_msg += 'Cvv' + ' ' + error_details.get('cvv2')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                elif 'error_message' in error:
                                    error_msg += error.get('error_message')
                                    raise ValidationError(_(error_msg))
                        elif resp.status_code == 401:
                            raise ValidationError(_("Credentials are missing or Invalid.."))
                        elif resp.status_code == 400:
                            if 'error_details' in error:
                                error_details = error.get('error_details')
                                if 'card' in error_details:
                                    error_msg += 'Card' + ' ' + error_details.get('card')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_month' in error_details:
                                    error_msg += 'Expiry Month' + ' ' + error_details.get('expiry_month')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_year' in error_details:
                                    error_msg += 'Expiry Year' + ' ' + error_details.get('expiry_year')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'cvv2' in error_details:
                                    error_msg += 'Cvv' + ' ' + error_details.get('cvv2')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                            elif 'error_message' in error:
                                error_msg += error.get('error_message')
                                raise ValidationError(_(error_msg))

                    if data:
                        resp = requests.post(transaction_url, json=data,
                                             auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                        if resp.status_code == 200:
                            error_status_code = json.loads(resp.text)
                            if error_status_code.get('status_code', False) == 'E':
                                payments.action_cancel()
                                if 'error_message' in error_status_code:
                                    error_message = error_status_code.get('error_message')
                                    raise ValidationError(_(error_message))
                            if self.pay_new_card:
                                card_no = self.credit_card_code
                            elif self.credit_card_details:
                                card_no = self.credit_card_details.credit_card_code
                            json_rec = resp.json()
                            # move_id = self.env['account.move'].search([('name', '=', payment_vals.get('ref'))])
                            if 'transaction' in json_rec:
                                transaction_rec = json_rec.get('transaction')
                                if 'transaction_details' in transaction_rec:
                                    type = transaction_rec.get('transaction_details').get('type')
                                if 'status_details' in transaction_rec:
                                    status = transaction_rec.get('status_details').get('status')
                            self.env['accept.blue.line'].create({
                                'pay_status': status if status else '',
                                'pay_type': type if type else '',
                                'pay_ref_no': json_rec.get('reference_number'),
                                'pay_auth_code': json_rec.get('auth_code'),
                                'pay_status_code': json_rec.get('status_code'),
                                'account_accept_move_id': move_id.id,
                                'card_no': card_no,
                                'paid_amount': payments.amount,
                                'refund_amount': payments.amount,
                                'credit_card_no_encr': credit_card_no
                            })
                            if sale_order_id:
                                sale_order_id.partner_id.accept_blue_creeate_cus_id = created_id
                            else:
                                move_id.partner_id.accept_blue_creeate_cus_id = created_id

                            payments.accept_blue_ref = json_rec.get('reference_number')
                        elif resp.status_code == 401:
                            raise ValidationError(_('Accept Blue Credentials Wrong'))
                        else:
                            error = json.loads(resp.text)
                            if 'error_details' in error:
                                error_details = error.get('error_details')
                                if 'card' in error_details:
                                    error_msg += 'Card' + ' ' + error_details.get('card')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_month' in error_details:
                                    error_msg += 'Expiry Month' + ' ' + error_details.get('expiry_month')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_year' in error_details:
                                    error_msg += 'Expiry Year' + ' ' + error_details.get('expiry_year')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'cvv2' in error_details:
                                    error_msg += 'Cvv' + ' ' + error_details.get('cvv2')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                            elif 'error_message' in error:
                                error_msg += error.get('error_message')
                                raise ValidationError(_(error_msg))
                elif self.origin_inv_id:
                    if self.accept_blue_reference_no:
                        error_msg = ''
                        # reverse_move_id = self.env['account.move'].browse(self.env.context.get('active_id'))
                        if self.amount > self.origin_inv_id.amount_total:
                            raise ValidationError(_('You can not Change Original Credit Note Amount'))
                        if self.accept_blue_reference_no:
                            if self.amount == 0:
                                raise ValidationError(_('Enter Valid Amount'))
                            if self.amount > self.accept_blue_reference_no.refund_amount:
                                raise ValidationError(
                                    _('You can not refund more than Remanining amount.. The remaining amount is {}'.format(
                                        self.accept_blue_reference_no.refund_amount)))
                        url = config_id.api_url + 'transactions/refund'
                        data = {
                            "reference_number": int(self.accept_blue_reference_no.pay_ref_no),
                            "amount": self.amount,
                            "cvv2": self.accept_blue_reference_no.card_no,
                            "customer": {
                                "send_receipt": False,
                                "email": self.partner_id.email,
                                "identifier": self.accept_blue_reference_no.account_accept_move_id.partner_id.name
                            },
                        }
                        resp = requests.post(url, json=data,
                                             auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                        json_rec = resp.json()
                        if 'transaction' in json_rec:
                            transaction_rec = json_rec.get('transaction')
                            if 'transaction_details' in transaction_rec:
                                type = transaction_rec.get('transaction_details').get('type')
                            if 'status_details' in transaction_rec:
                                status = transaction_rec.get('status_details').get('status')
                        error = json.loads(resp.text)
                        if 'error_details' in error:
                            error_details = error.get('error_details')
                            if 'customer.email' in error_details:
                                error_msg += 'customer.email' + ' ' + error_details.get('customer.email')[0] + ' ,'
                            raise ValidationError(_(error_msg))
                        else:
                            json_rec = resp.json()
                            self.accept_blue_reference_no.refund_amount = abs(
                                self.accept_blue_reference_no.refund_amount - self.amount)
                            self.env['accept.blue.line'].create({
                                'pay_status': 'Captured',
                                'pay_type': 'Refund',
                                'pay_ref_no': json_rec.get('reference_number'),
                                'pay_auth_code': json_rec.get('auth_code'),
                                'pay_status_code': json_rec.get('status_code'),
                                'paid_amount': self.amount,
                                'refund_amount': self.amount,
                                'account_accept_move_id': self.accept_blue_reference_no.account_accept_move_id.id,
                                'card_no': self.accept_blue_reference_no.card_no,
                                'paid_amount': self.amount,
                                'refund_amount': self.amount,
                                'original_pay_ref': self.accept_blue_reference_no.pay_ref_no
                            })
                            payments.accept_blue_ref = json_rec.get('reference_number')
            else:
                raise ValidationError(_("Please configure accept blue credentials.."))

    def expired_status(self,error_message):
        self.credit_card_details.write({'credit_card_exp_status':'expired'})
        raise ValidationError(_(error_message))
    def _accept_blue_transaction(self,config_id,payments):
        error_msg=''
        created_id=''
        credit_card_no = ''
        if self.payment_method_line_id.is_accept_blue_payment:
            if config_id:
                if not self.origin_inv_id and not self.is_direct_credit_note:
                    move_id = self.in_invoice_id[0]
                    if move_id:
                        sale_order_id = self.env['sale.order'].search([('name', '=', move_id.invoice_origin)])
                        if sale_order_id:
                            created_cus_accept_blue_id = sale_order_id.partner_id.accept_blue_creeate_cus_id
                        else:
                            created_cus_accept_blue_id = move_id.partner_id.accept_blue_creeate_cus_id
                        if created_cus_accept_blue_id:
                            exist_cus_id = self.get_customer_rec(config_id, move_id)
                            if exist_cus_id == created_cus_accept_blue_id:
                                created_id = created_cus_accept_blue_id
                            else:
                                created_id = self.create_customer_rec(config_id, move_id)
                                if created_id:
                                    sale_order_id.partner_id.accept_blue_creeate_cus_id = created_id
                                    created_id = created_id
                                else:
                                    created_id = ''
                        else:
                            created_id = self.create_customer_rec(config_id, move_id)
                            if created_id:
                                sale_order_id.partner_id.accept_blue_creeate_cus_id = created_id
                                created_id = created_id
                            else:
                                created_id = ''
                    # account_move_id=self.env['account.move'].search([('name','=',self.communication)])
                    account_move_id = self.in_invoice_id
                    if account_move_id:
                        pass
                        # if self.amount > account_move_id.amount_residual:
                        #     raise ValidationError(_('You can not change original amount'))
                    if not self.credit_card_details and not self.pay_new_card:
                        raise ValidationError(_("Please select Card Details For Payments.."))
                    transaction_url = config_id.api_url + 'transactions/charge'
                    if not self.pay_new_card:
                        if self.credit_card_details:
                            if self.credit_card_details.credit_card_expiration_year.isdigit():
                                expiry_year = int('20' + self.credit_card_details.credit_card_expiration_year)
                            else:
                                raise ValidationError(_('Please Put Valid Expiry year'))
                            data = {
                                'amount': self.amount,
                                'expiry_month': int(self.credit_card_details.credit_card_expiration_month),
                                'expiry_year': expiry_year,
                                'cvv2': self.credit_card_details.credit_card_code,
                                'source': 'tkn-' + self.credit_card_details.access_token,
                                "customer": {
                                    "customer_id": created_id
                                },
                                "transaction_details": {
                                    "invoice_number": payments.name if self.can_group_payments else self.communication
                                }
                            }
                            credit_card_no = self.credit_card_details.credit_card_no

                    elif self.pay_new_card and self.store_card:
                        exist_card_details=self.env['card.details'].search([('credit_card_expiration_month','=',self.credit_card_expiration_month),('credit_card_expiration_year','=',self.credit_card_expiration_year),('credit_card_code','=',self.credit_card_code),('partner_id','=',self.partner_id.id)])
                        if exist_card_details:
                            for esxt_card in exist_card_details:
                                if esxt_card:
                                    card_no = self.credit_card_no[-4:]
                                    exist_card_detail_card_no=esxt_card.credit_card_no[-4:]
                                    if card_no == exist_card_detail_card_no:
                                        raise ValidationError(_('Card Already Existing..'))
                        card_details = self.store_credit_card_details()
                        if self.credit_card_expiration_year.isdigit():
                            expiry_year = int('20' + self.credit_card_expiration_year)
                        else:
                            raise ValidationError(_('Please Put Valid Expiry year'))
                        if card_details:
                            data = {
                                'amount': self.amount,
                                'expiry_month': int(self.credit_card_expiration_month),
                                'expiry_year': expiry_year,
                                'cvv2': card_details.credit_card_code,
                                'source': 'tkn-' + card_details.access_token,

                                "customer": {
                                    "customer_id": created_id
                                },
                                "transaction_details": {
                                    "invoice_number": payments.name if self.can_group_payments else self.communication
                                }
                            }

                            credit_card_no = card_details.credit_card_no
                    elif self.pay_new_card and not self.store_card:
                        if self.credit_card_expiration_year.isdigit():
                            expiry_year = int('20' + self.credit_card_expiration_year)
                        else:
                            raise ValidationError(_('Please Put Valid Expiry year'))
                        expiry_month = int(self.credit_card_expiration_month)
                        data = {
                            'expiry_month': expiry_month,
                            'expiry_year': expiry_year,
                            'card': self.credit_card_no,
                            "cvv2": self.credit_card_code,
                            'save_card': True
                        }
                        credit_card_no = self.credit_card_no
                        url = config_id.api_url + 'transactions/verify'
                        resp = requests.post(url, json=data,
                                             auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                        res_text = json.loads(resp.text)
                        error = json.loads(resp.text)
                        if resp.status_code == 200:
                            if res_text.get('status_code') == 'A':
                                data = {
                                    'amount': self.amount,
                                    'expiry_month': int(self.credit_card_expiration_month),
                                    'expiry_year': expiry_year,
                                    'cvv2': self.credit_card_code,
                                    'source': 'tkn-' + res_text.get('card_ref'),

                                    "customer": {
                                        "customer_id": created_id
                                    },
                                    "transaction_details": {
                                         "invoice_number": payments.name if self.can_group_payments else self.communication
                                    }
                                }
                                lst_4_digi = self.credit_card_no[-4:].rjust(len(self.credit_card_no), '*')
                                credit_card_no =lst_4_digi
                            else:
                                if 'error_details' in error:
                                    error_details = error.get('error_details')
                                    if 'card' in error_details:
                                        error_msg += 'Card' + ' ' + error_details.get('card')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                    if 'expiry_month' in error_details:
                                        error_msg += 'Expiry Month' + ' ' + error_details.get('expiry_month')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                    if 'expiry_year' in error_details:
                                        error_msg += 'Expiry Year' + ' ' + error_details.get('expiry_year')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                    if 'cvv2' in error_details:
                                        error_msg += 'Cvv' + ' ' + error_details.get('cvv2')[0] + ' ,'
                                        raise ValidationError(_(error_msg))
                                elif 'error_message' in error:
                                    error_msg += error.get('error_message')
                                    raise ValidationError(_(error_msg))
                        elif resp.status_code == 401:
                            raise ValidationError(_("Credentials are missing or Invalid.."))
                        elif resp.status_code == 400:
                            if 'error_details' in error:
                                error_details = error.get('error_details')
                                if 'card' in error_details:
                                    error_msg += 'Card' + ' ' + error_details.get('card')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_month' in error_details:
                                    error_msg += 'Expiry Month' + ' ' + error_details.get('expiry_month')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_year' in error_details:
                                    error_msg += 'Expiry Year' + ' ' + error_details.get('expiry_year')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'cvv2' in error_details:
                                    error_msg += 'Cvv' + ' ' + error_details.get('cvv2')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                            elif 'error_message' in error:
                                error_msg += error.get('error_message')
                                raise ValidationError(_(error_msg))

                    if data:
                        resp = requests.post(transaction_url, json=data,
                                             auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                        if resp.status_code == 200:
                            error_status_code=json.loads(resp.text)
                            if error_status_code.get('status_code',False)=='E':
                                if 'error_message' in error_status_code:
                                    payments.action_cancel()
                                    error_message = error_status_code.get('error_message')
                                    if error_message == 'Token not found' and self.credit_card_details:
                                        self.expired_status(error_message)
                            if error_status_code.get('status_code', False) == 'D':
                                raise ValidationError(_('Payment has been declined'))
                                        # self.credit_card_details.credit_card_exp_status='expired'

                            if self.pay_new_card:
                                card_no = self.credit_card_code
                            elif self.credit_card_details:
                                card_no = self.credit_card_details.credit_card_code
                            json_rec = resp.json()
                            # move_id = self.env['account.move'].search([('name', '=', payment_vals.get('ref'))])
                            move_id = self.in_invoice_id
                            type=''
                            status = ''
                            if 'transaction' in json_rec:
                                transaction_rec = json_rec.get('transaction')
                                if 'transaction_details' in transaction_rec:
                                    type = transaction_rec.get('transaction_details').get('type')
                                if 'status_details' in transaction_rec:
                                    status = transaction_rec.get('status_details').get('status')
                            for line in self.in_invoice_id:
                                self.env['accept.blue.line'].create({
                                    'pay_status': status if status else '',
                                    'pay_type': type if type else '',
                                    'pay_ref_no': json_rec.get('reference_number'),
                                    'pay_auth_code': json_rec.get('auth_code'),
                                    'pay_status_code': json_rec.get('status_code'),
                                    'account_accept_move_id': line.id,
                                    'card_no': card_no,
                                    'paid_amount': self.amount,
                                    'refund_amount': self.amount,
                                    'credit_card_no_encr': credit_card_no
                                })
                            if sale_order_id:
                                sale_order_id.partner_id.accept_blue_creeate_cus_id = created_id
                            else:
                                move_id.partner_id.accept_blue_creeate_cus_id = created_id

                            payments.accept_blue_ref = json_rec.get('reference_number')
                        elif resp.status_code == 401:
                            raise ValidationError(_('Accept Blue Credentials Wrong'))
                        else:
                            error = json.loads(resp.text)
                            if 'error_details' in error:
                                error_details = error.get('error_details')
                                if 'card' in error_details:
                                    error_msg += 'Card' + ' ' + error_details.get('card')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_month' in error_details:
                                    error_msg += 'Expiry Month' + ' ' + error_details.get('expiry_month')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'expiry_year' in error_details:
                                    error_msg += 'Expiry Year' + ' ' + error_details.get('expiry_year')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'cvv2' in error_details:
                                    error_msg += 'Cvv' + ' ' + error_details.get('cvv2')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                if 'amount' in error_details:
                                    error_msg += 'amount' + ' ' + error_details.get('amount')[0] + ' ,'
                                    raise ValidationError(_(error_msg))
                                else:
                                    raise ValidationError(_('something is Wrong'))
                            elif 'error_message' in error:
                                error_msg += error.get('error_message')
                                raise ValidationError(_(error_msg))
                elif self.origin_inv_id:
                    if self.accept_blue_reference_no:
                        error_msg = ''
                        # reverse_move_id = self.env['account.move'].browse(self.env.context.get('active_id'))
                        if self.amount > self.origin_inv_id.amount_total:
                            raise ValidationError(_('You can not Change Original Credit Note Amount'))
                        if self.accept_blue_reference_no:
                            if self.amount == 0:
                                raise ValidationError(_('Enter Valid Amount'))
                            if self.amount > self.accept_blue_reference_no.refund_amount:
                                raise ValidationError(
                                    _('You can not refund more than Remanining amount.. The remaining amount is {}'.format(
                                        self.accept_blue_reference_no.refund_amount)))
                        url = config_id.api_url + 'transactions/refund'
                        data = {
                            "reference_number": int(self.accept_blue_reference_no.pay_ref_no),
                            "amount": self.amount,
                            "cvv2": self.accept_blue_reference_no.card_no,
                            "customer": {
                                "send_receipt": False,
                                "email": self.partner_id.email,
                                "identifier": self.accept_blue_reference_no.account_accept_move_id.partner_id.name
                            },
                        }
                        resp = requests.post(url, json=data,
                                             auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                        json_rec = resp.json()
                        if 'transaction' in json_rec:
                            transaction_rec = json_rec.get('transaction')
                            if 'transaction_details' in transaction_rec:
                                type = transaction_rec.get('transaction_details').get('type')
                            if 'status_details' in transaction_rec:
                                status = transaction_rec.get('status_details').get('status')
                        error = json.loads(resp.text)
                        if 'error_details' in error:
                            error_details = error.get('error_details')
                            if 'customer.email' in error_details:
                                error_msg += 'customer.email' + ' ' + error_details.get('customer.email')[0] + ' ,'
                            raise ValidationError(_(error_msg))
                        else:
                            json_rec = resp.json()
                            acce_blue_line_ids=self.env['accept.blue.line'].search([('pay_ref_no','=',self.accept_blue_reference_no.pay_ref_no)])
                            for acc_blue_id in acce_blue_line_ids:
                                acc_blue_id.refund_amount = abs(
                                    acc_blue_id.refund_amount - self.amount)
                            if len(acce_blue_line_ids)>1:
                                for acpt_blue_line in acce_blue_line_ids:
                                    self.env['accept.blue.line'].create({
                                        'pay_status': 'Captured',
                                        'pay_type': 'Refund',
                                        'pay_ref_no': json_rec.get('reference_number'),
                                        'pay_auth_code': json_rec.get('auth_code'),
                                        'pay_status_code': json_rec.get('status_code'),
                                        'paid_amount': self.amount,
                                        'refund_amount': self.amount,
                                        'account_accept_move_id': acpt_blue_line.account_accept_move_id.id,
                                        'card_no': self.accept_blue_reference_no.card_no,
                                        'paid_amount': self.amount,
                                        'refund_amount': self.amount,
                                        'original_pay_ref': self.accept_blue_reference_no.pay_ref_no
                                    })
                            else:
                                self.env['accept.blue.line'].create({
                                    'pay_status': 'Captured',
                                    'pay_type': 'Refund',
                                    'pay_ref_no': json_rec.get('reference_number'),
                                    'pay_auth_code': json_rec.get('auth_code'),
                                    'pay_status_code': json_rec.get('status_code'),
                                    'paid_amount': self.amount,
                                    'refund_amount': self.amount,
                                    'account_accept_move_id': self.accept_blue_reference_no.account_accept_move_id.id,
                                    'card_no': self.accept_blue_reference_no.card_no,
                                    'paid_amount': self.amount,
                                    'refund_amount': self.amount,
                                    'original_pay_ref': self.accept_blue_reference_no.pay_ref_no
                                })
                            payments.accept_blue_ref = json_rec.get('reference_number')
            else:
                raise ValidationError(_("Please configure accept blue credentials.."))

    def _create_payments(self):
        status=''
        type=''
        card_details=False
        error_msg=''
        config_id = self.env['accept.blue.config'].search([])
        self.ensure_one()
        batches = self._get_batches()
        first_batch_result = batches[0]
        edit_mode = self.can_edit_wizard and (len(first_batch_result['lines']) == 1 or self.group_payment)
        to_process = []
        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
            to_process.append({
                'create_vals': payment_vals,
                'to_reconcile': first_batch_result['lines'],
                'batch': first_batch_result,
            })
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'payment_values': {
                                **batch_result['payment_values'],
                                'payment_type': 'inbound' if line.balance > 0 else 'outbound'
                            },
                            'lines': line,
                        })
                batches = new_batches

            for batch_result in batches:
                to_process.append({
                    'create_vals': self._create_payment_vals_from_batch(batch_result),
                    'to_reconcile': batch_result['lines'],
                    'batch': batch_result,
                })
        payments = self._init_payments(to_process, edit_mode=edit_mode)
        self._post_payments(to_process, edit_mode=edit_mode)
        self._reconcile_payments(to_process, edit_mode=edit_mode)
        if self.payment_method_line_id.is_accept_blue_payment:
            if len(self.in_invoice_id.mapped('partner_id')) > 1:
                raise ValidationError(_("You can not register payment with different customer .."))
            else:
                if self.group_payment:
                    self._accept_blue_transaction(config_id,payments)
                else:
                    for payment_id in payments:
                        self._accept_blue_transaction_not_group_payment(config_id,payment_id)

        return payments


    def action_save_card(self):
        register_payment_id=self.env['account.register.payment'].browse(self.env.context.get('active_id'))
        account_move_id=self.env['account.move'].search([('name','=',register_payment_id.communication)])
        config_id = self.env['accept.blue.config'].search([])
        if config_id:
            url = config_id.api_url + 'saved-cards'
        if register_payment_id.credit_card_no:
            data = {
                'expiry_month': int(register_payment_id.credit_card_expiration_month),
                'expiry_year': int(register_payment_id.credit_card_expiration_year),
                'card': register_payment_id.credit_card_no
            }
            url = config_id.api_url + 'saved-cards'
            resp = requests.post(url, json=data, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
            if resp.status_code == 200:
                json_rec = resp.json()
                access_token = json_rec.get('cardRef')

                lst_4_digi = register_payment_id.credit_card_no[-4:].rjust(len(register_payment_id.credit_card_no), '*')
                data.update({
                    'access_token': access_token,
                    'credit_card_no':lst_4_digi
                             })
                if account_move_id:
                    self.env['card.details'].create(data)
            else:
                error = json.loads(resp.text)
                if error:
                    raise ValidationError(_(error.get('error_message')))



class AccountMove(models.Model):
    _inherit='account.move'


    accept_blue_details_id=fields.One2many('accept.blue.line','account_accept_move_id')
    origin_inv_id=fields.Many2one('account.move')

    def copy_data(self, default=None):
        if 'invoice_origin' not in default:
            default['invoice_origin'] = False
        return super(AccountMove, self).copy_data(default)


    def refund_credit_card_transaction(self):
        config_id = self.env['accept.blue.config'].search([])
        if config_id:
            url = config_id.api_url + 'transactions/refund'
            data = {
                "reference_number": self.pay_ref_no,
                "amount": self.amount_total,
                "cvv2": "123",
                "customer": {
                    "send_receipt": False,
                    "email":self.partner_id.email,
                }
            }
            resp = requests.post(url, json=data, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
            if not resp.status_code==200:
                error = json.loads(resp.text)
                if error:
                    raise ValidationError(_(error.get('error_message')))

        else:
            raise ValidationError(_("Please configure accept blue credentials.."))




class AcceptBlueLine(models.Model):
    _name='accept.blue.line'
    _rec_name='pay_ref_no'

    pay_status = fields.Char('Status')
    pay_type=fields.Char('Type')
    pay_ref_no = fields.Char('Transaction ID')
    pay_auth_code = fields.Char('Auth Number')
    pay_status_code = fields.Char('Status Code')
    account_accept_move_id=fields.Many2one('account.move')
    amount = fields.Float('Amount')
    paid_amount=fields.Monetary(currency_field='currency_id')
    card_no=fields.Char('Cvv')
    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)
    refund_amount=fields.Float('remaining Amount',digits=(12,2) )
    original_pay_ref=fields.Char('Reference Number')
    credit_card_no_encr=fields.Char('Reference Number')


    def _cron_accept_blue_settle_transaction(self):
        config_id = self.env['accept.blue.config'].search([])
        if config_id:
            accept_blue_ids=self.env['accept.blue.line'].search([('pay_status','=','captured')])
            for line in accept_blue_ids:
                url = config_id.api_url + 'transactions/' + line.pay_ref_no
                resp = requests.get(url, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                if resp.status_code==200:
                    api_resp = resp.json()
                    if 'status_details' in api_resp:
                        status=api_resp.get('status_details').get('status')
                        line.write({"pay_status":status})
        else:
            raise ValidationError(_("Please configure accept blue credentials.."))

    def name_get(self):
        result = []
        for rec in self:
            name = rec.pay_ref_no + '-' + rec.currency_id.symbol + str(rec.refund_amount)
            result.append((rec.id, name))
        return result

    def void_credit_card_transaction(self):
        config_id=self.env['accept.blue.config'].search([])
        if config_id:
            url=config_id.api_url + 'transactions/void'
            data={
                "reference_number": int(self.pay_ref_no),
                "customer": {
                    "send_receipt": False,
                    "email": self.account_accept_move_id.partner_id.email,
                }
            }
            resp = requests.post(url, json=data, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
            if resp.status_code==200:
                api_resp=resp.json()
                if api_resp.get('status_code') =='A':
                    payment_id=self.env['account.payment'].search([('accept_blue_ref','=',self.pay_ref_no)])
                    if payment_id:
                        payment_id.action_draft()
                        payment_id.action_cancel()
                    # self.button_draft()
                    accept_blue_line_ids=self.env['accept.blue.line'].search([('pay_ref_no','=',self.pay_ref_no)])
                    accept_blue_line_ids.write({
                         'pay_status':'Voided',
                        'pay_status_code': api_resp.get('status_code')
                    })
                    blue_line_orig_id=self.env['accept.blue.line'].search([('pay_ref_no','=',self.original_pay_ref)])
                    if blue_line_orig_id:
                        for acc_blue_rec in blue_line_orig_id:
                            acc_blue_rec.refund_amount=acc_blue_rec.refund_amount + self.paid_amount
                elif api_resp.get('status_code') == 'E':
                    raise ValidationError(_(api_resp.get('error_message')))
                elif api_resp.get('status_code') == 'D':
                    raise ValidationError(_(api_resp.get('error_message')))
            else:
                error = json.loads(resp.text)
                if error:
                    raise ValidationError(_(error.get('error_message') + str(error.get('error_details'))))

        else:
            raise ValidationError(_("Please configure accept blue credentials.."))



class AccountPayment(models.Model):
    _inherit='account.payment'

    accept_blue_ref=fields.Char('Accept Blue Reference')


class AccountMoveReversal(models.TransientModel):
    _inherit='account.move.reversal'

    origin_inv_id = fields.Many2one('account.move')

    # @api.model
    # def default_get(self, fields):
    #     res = super(AccountMoveReversal, self).default_get(fields)
    #     res.update({'origin_inv_id':self.env.context.get('active_id')})
    #     return res

    # def reverse_moves(self):
    #     self.ensure_one()
    #     moves = self.move_ids
    #     # if self.origin_inv_id:
    #     #     moves.write({
    #     #         'origin_inv_id':self.origin_inv_id.id
    #     #     })
    #
    #     # Create default values.
    #     default_values_list = []
    #     for move in moves:
    #         default_values_list.append(self._prepare_default_reversal(move))
    #
    #     batches = [
    #         [self.env['account.move'], [], True],  # Moves to be cancelled by the reverses.
    #         [self.env['account.move'], [], False],  # Others.
    #     ]
    #     for move, default_vals in zip(moves, default_values_list):
    #         is_auto_post = default_vals.get('auto_post') != 'no'
    #         is_cancel_needed = not is_auto_post and self.refund_method in ('cancel', 'modify')
    #         batch_index = 0 if is_cancel_needed else 1
    #         batches[batch_index][0] |= move
    #         batches[batch_index][1].append(default_vals)
    #
    #     # Handle reverse method.
    #     moves_to_redirect = self.env['account.move']
    #     for moves, default_values_list, is_cancel_needed in batches:
    #         new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)
    #
    #         if self.refund_method == 'modify':
    #             moves_vals_list = []
    #             for move in moves.with_context(include_business_fields=True):
    #                 moves_vals_list.append(
    #                     move.copy_data({'date': self.date if self.date_mode == 'custom' else move.date})[0])
    #             new_moves = self.env['account.move'].create(moves_vals_list)
    #
    #         moves_to_redirect |= new_moves
    #
    #     self.new_move_ids = moves_to_redirect
    #
    #     # Create action.
    #     action = {
    #         'name': _('Reverse Moves'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'account.move',
    #     }
    #     if len(moves_to_redirect) == 1:
    #         action.update({
    #             'view_mode': 'form',
    #             'res_id': moves_to_redirect.id,
    #             'context': {'default_move_type': moves_to_redirect.move_type},
    #         })
    #     else:
    #         action.update({
    #             'view_mode': 'tree,form',
    #             'domain': [('id', 'in', moves_to_redirect.ids)],
    #         })
    #         if len(set(moves_to_redirect.mapped('move_type'))) == 1:
    #             action['context'] = {'default_move_type': moves_to_redirect.mapped('move_type').pop()}
    #     return action



class AccountPaymentMethodLine(models.Model):
    _inherit='account.payment.method.line'

    is_accept_blue_payment=fields.Boolean('Is accept blue ??')



