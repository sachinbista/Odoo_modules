# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'

    fedex_bill_my_account = fields.Boolean(string='Bill My Account',
                                           help="If checked, ecommerce users will be prompted their Fedex account\n"
                                                "number and delivery fees will be charged on it.")