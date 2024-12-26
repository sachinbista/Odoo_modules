# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    is_emailed = fields.Boolean()