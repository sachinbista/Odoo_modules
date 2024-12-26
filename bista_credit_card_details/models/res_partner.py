# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
import logging
import uuid
from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # def action_send_credit_card_form(self):
    #     template = self.env.ref('bista_credit_card_details.email_template_credit_card_form')
    #     for partner in self:
    #         link = f"/form/credit_card?partner_id={partner.id}"
    #         template.sudo().send_mail(partner.id, force_send=True, email_values={
    #             'email_to': partner.email,
    #             'body_html': f"Dear {partner.name},<br><br>"
    #                          f"Please click the link below to fill out your credit card details:<br>"
    #                          f"<a href='{link}'>Submit Credit Card Information</a><br><br>"
    #                          f"Thank you!",
    #         })

    credit_card_token = fields.Char("Credit Card Form Token")

    def action_send_credit_card_form(self):
        template = self.env.ref('bista_credit_card_details.email_template_credit_card_form')
        for partner in self:
            token = str(uuid.uuid4())
            partner.credit_card_token = token
            link = f"/form/credit_card?partner_id={partner.id}&token={token}"
            template.sudo().send_mail(partner.id, force_send=True, email_values={
                'email_to': partner.email,
                'body_html': f"Dear {partner.name},<br><br>"
                             f"Please click the link below to fill out your credit card details:<br>"
                             f"<a href='{link}'>Submit Credit Card Information</a><br><br>"
                             f"Thank you!",
            })