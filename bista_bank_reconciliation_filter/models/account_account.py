# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions
# Copyright (C) 2021 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, api, fields
from odoo.osv import expression

class AccountAccount(models.Model):
    _inherit = "account.account"

    allow_bank_reconciliation = fields.Boolean(
        'Allow Bank Reconciliation', copy=False)