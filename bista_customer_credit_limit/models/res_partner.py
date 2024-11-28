# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_check = fields.Boolean('Active Credit', help='Activate the credit limit feature')

    # Todo: Remove Blocking field it is not longer used
    credit_blocking = fields.Monetary('Blocking Amount')
    credit_blocking_message = fields.Text()

    @api.constrains('credit_blocking')
    def _check_credit_amount(self):
        for credit in self:
            if credit.credit_blocking < 0:
                raise ValidationError(_('Blocking amount should not be less than zero.'))
