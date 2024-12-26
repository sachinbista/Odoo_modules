from odoo import api, fields, models, _
from requests.auth import HTTPBasicAuth
import requests
import json
from odoo.exceptions import AccessError, UserError, ValidationError
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




class ResPartner(models.Model):
    _inherit='res.partner'

    card_detail_id=fields.One2many('card.details','partner_id')
    accept_blue_creeate_cus_id = fields.Integer('Accept blue customer id')

    def create_access_token(self):
        config_id = self.env['accept.blue.config'].search([])
        if config_id:
            url = config_id.api_url + 'saved-cards'
        for line in self.card_detail_id:
            data = {
                'expiry_month':int(line.credit_card_expiration_month),
                'expiry_year':int(line.credit_card_expiration_year),
                'card':line.credit_card_no
            }
            resp = requests.post(url, json=data, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
            if resp.status_code==200:
                json_rec = resp.json()
                line.access_token=json_rec.get('cardRef')
            lst_4_digi = line.credit_card_no[-4:].rjust(len(line.credit_card_no), '*')
            line.write({
                'credit_card_no':lst_4_digi
            })


class AcceptBlueCardDetails(models.Model):
    _name='card.details'
    _rec_name='credit_card_no'


    partner_id=fields.Many2one('res.partner')
    credit_card_no = fields.Char('Card Number', size=16)
    credit_card_code = fields.Char('CVV', size=4)
    credit_card_type = fields.Selection([
                                ('americanexpress', 'American Express'),
                                ('visa', 'Visa'),
                                ('mastercard', 'Mastercard'),
                                ('discover', 'Discover'),
                                ('dinersclub', 'Diners Club'),
                                ('union','Union'),
                                ('jcb', 'JCB')], 'Card Type',required=True)

    credit_card_expiration_month = fields.Selection([('01', '01'), ('02', '02'), ('03', '03'), ('04', '04'),
                                                     ('05', '05'), ('06', '06'), ('07', '07'), ('08', '08'),
                                                     ('09', '09'), ('10', '10'), ('11', '11'), ('12', '12'),
                                                     ], 'Expires Month')

    credit_card_expiration_year = fields.Char('Expires Year', size=2)

    is_accept_blue_cus = fields.Boolean('Is accept blue customer ??')
    accept_blue_cus_id = fields.Char('Customer Id')
    access_token=fields.Char('Access Token',compute='_get_access_token',store=True)
    is_access_token=fields.Boolean('is_access_token',compute='_compute_is_access_token')

    # credit_card_expiration_status = fields.Selection([
    #     ('expired', 'Expired')], 'Card Status')

    credit_card_exp_status = fields.Char('Status')

    @api.onchange('credit_card_no')
    def _onchange_card_no(self):
        for line in self:
            if line.credit_card_no:
                card_type = cc_type(line.credit_card_no)
                if card_type:
                    line.credit_card_type = card_type


    @api.depends('access_token')
    def _compute_is_access_token(self):
        for line in self:
            if line.access_token:
                line.is_access_token=True
            else:
                line.is_access_token=False

    # def generate_access_token(self,resp):
    #     json_rec = resp.json()
    #     lst_4_digi = self.credit_card_no[-4:].rjust(len(self.credit_card_no), '*')
    #     self.write({
    #         'credit_card_no': lst_4_digi,
    #         'access_token':json_rec.get('card_ref')
    #     })

    def verify_card_details(self,config_id):
        error_msg=''
        for line in self:
            expiry_month=int(line.credit_card_expiration_month)
            if line.credit_card_expiration_year.isdigit():
                expiry_year=int('20' + line.credit_card_expiration_year)
            else:
                raise ValidationError(_('Please Put Valid Expiry year'))
            data = {
                'expiry_month': expiry_month,
                'expiry_year': expiry_year,
                'card': line.credit_card_no,
                "cvv2": line.credit_card_code,
                'save_card':True
            }
            url = config_id.api_url + 'transactions/verify'
            resp = requests.post(url, json=data, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
            res_text = json.loads(resp.text)
            error = json.loads(resp.text)
            if resp.status_code==200:
                if res_text.get('status_code')=='A':
                    lst_4_digi = self.credit_card_no[-4:].rjust(len(self.credit_card_no), '*')
                    self.write({
                        'credit_card_no': lst_4_digi,
                        'access_token': res_text.get('card_ref')
                    })
                else:
                    if 'error_details' in error:
                        error_details=error.get('error_details')
                        if 'card' in error_details:
                            error_msg += 'Card' + ' ' +  error_details.get('card')[0] + ' ,'
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



    @api.depends('credit_card_code','credit_card_no','credit_card_expiration_month','credit_card_expiration_year')
    def _get_access_token(self):
        config_id = self.env['accept.blue.config'].search([])
        if config_id:
            url = config_id.api_url + 'saved-cards'
            for line in self:
                if line.credit_card_type:
                    if line.credit_card_no and line.credit_card_expiration_month and line.credit_card_expiration_year and line.credit_card_code and not line.access_token:
                        self.verify_card_details(config_id)

                        # data = {
                        #     'expiry_month': int(line.credit_card_expiration_month),
                        #     'expiry_year': int(line.credit_card_expiration_year),
                        #     'card': line.credit_card_no,
                        #     ''
                        # }
                        # url=config_id.api_url + 'saved-cards'
                        # resp = requests.post(url, json=data, auth=HTTPBasicAuth(config_id.source_key, config_id.pin_code))
                        # if resp.status_code == 200:
                        #    self.generate_access_token(resp)
                        # elif resp.status_code == 401:
                        #     raise ValidationError(_("Credentials are missing or Invalid.."))
        else:
            raise ValidationError(_("Please configure accept blue credentials.."))
