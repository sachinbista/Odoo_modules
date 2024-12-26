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

    auto_create_invoice = fields.Boolean("Auto Create Customer Invoice")
    auto_validate_invoice = fields.Boolean("Auto Validate Customer Invoice")
    auto_send_mail_invoice = fields.Boolean("Auto Send Mail Customer Invoice")
