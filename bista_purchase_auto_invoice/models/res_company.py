# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2020 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    auto_create_bill = fields.Boolean("Auto Create Vendor Bill")
    auto_validate_bill = fields.Boolean("Auto Validate Vendor Bill")
    auto_send_mail_bill = fields.Boolean("Auto Send Mail Vendor Bill")
