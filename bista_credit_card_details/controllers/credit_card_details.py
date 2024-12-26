# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.authorize_net.models import misc
class CreditCardController(http.Controller):

    # @http.route('/form/credit_card', type='http', auth='public', website=True)
    # def credit_card_form(self, **kwargs):
    #     partner_id = kwargs.get('partner_id')
    #     partner = request.env['res.partner'].browse(int(partner_id))
    #     return request.render('bista_credit_card_details.credit_card_form', {
    #         'partner_id': partner_id,
    #         'partner_name': partner.name,
    #     })
    #
    # @http.route('/submit/credit_card', type='http', auth="public", website=True)
    # def submit_credit_card(self,  **kwargs):
    #     partner_id = kwargs.get('partner_id')
    #     card_number = kwargs.get('card_number')
    #     card_type = kwargs.get('card_type')
    #     expiry_moth = kwargs.get('expiry_month')
    #     expiry_year = kwargs.get('expiry_year')
    #     cvv = kwargs.get('cvv')
    #
    #     partner = request.env['res.partner'].browse(int(partner_id))
    #     provider = request.env['payment.provider'].search([('code','=', 'authorize'),('name','=','Authorize.net')],limit=1)
    #     payment_method = request.env['payment.method'].search([('code','=', 'card')],limit=1)
    #     partner.payment_token_ids.create({
    #         'partner_id': partner.id,
    #         'credit_card_no': card_number,
    #         'credit_card_type': card_type,
    #         'default_payment_token': True,
    #         'provider_id': provider.id,
    #         'payment_method_id': payment_method.id,
    #         'provider_ref': 'dummy',
    #         'customer_profile_id': partner.authorize_partner_ids.customer_profile_id,
    #         'payment_details': str(misc.masknumber(card_number)) if card_number else None,
    #         'credit_card_expiration_month': expiry_moth,
    #         'credit_card_expiration_year': expiry_year,
    #         'authorize_payment_method_type': 'credit_card',
    #         'credit_card_code': cvv,
    #     })
    #     return request.redirect('/thank-you')
    #
    # @http.route('/thank-you', type='http', auth='public', website=True)
    # def thank_you(self):
    #     return "Thank you! Your credit card details have been successfully submitted."

    @http.route('/form/credit_card', type='http', auth='public', website=True)
    def credit_card_form(self, **kwargs):
        partner_id = kwargs.get('partner_id')
        token = kwargs.get('token')
        partner = request.env['res.partner'].sudo().browse(int(partner_id))
        if partner and partner.credit_card_token == token:
            return request.render('bista_credit_card_details.credit_card_form', {
                'partner_id': partner_id,
                'partner_name': partner.name,
            })
        return request.redirect('/invalid-token')

    @http.route('/submit/credit_card', type='http', auth="public", website=True, csrf=False)
    def submit_credit_card(self, **kwargs):
        partner_id = kwargs.get('partner_id')
        card_number = kwargs.get('card_number')
        card_type = kwargs.get('card_type')
        expiry_month = kwargs.get('expiry_month')
        expiry_year = kwargs.get('expiry_year')
        cvv = kwargs.get('cvv')

        # Fetch the partner record
        partner = request.env['res.partner'].sudo().browse(int(partner_id))

        # Verify partner exists and token matches
        if not partner:
            return request.redirect('/invalid-token')

        # Save credit card details in payment token
        provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'authorize'), ('name', '=', 'Authorize.net')], limit=1)
        payment_method = request.env['payment.method'].sudo().search([('code', '=', 'card')], limit=1)
        partner.payment_token_ids.sudo().create({
            'partner_id': partner.id,
            'credit_card_no': card_number,
            'credit_card_type': card_type,
            'default_payment_token': True,
            'provider_id': provider.id,
            'payment_method_id': payment_method.id,
            'provider_ref': 'dummy',
            'customer_profile_id': partner.authorize_partner_ids.customer_profile_id,
            'payment_details': str(misc.masknumber(card_number)) if card_number else None,
            'credit_card_expiration_month': expiry_month,
            'credit_card_expiration_year': expiry_year,
            'authorize_payment_method_type': 'credit_card',
            'credit_card_code': cvv,
        })

        partner.sudo().write({'credit_card_token': False})

        return request.redirect('/thank-you')

    @http.route('/invalid-token', type='http', auth='public', website=True)
    def invalid_token(self):
        return "Invalid or expired token. Please contact support for assistance."

    @http.route('/thank-you', type='http', auth='public', website=True)
    def thank_you(self):
        return "Thank you! Your credit card details have been successfully submitted."
