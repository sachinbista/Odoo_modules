# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    allow_delivery_validate_without_full_payment = fields.Boolean(string="Restrict Delivery Validate Without Full Payment")

