# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'


    state = fields.Selection(selection_add=[
        ('credit_review', 'Credit Review'),
    ], ondelete={'credit_review': 'cascade'})




