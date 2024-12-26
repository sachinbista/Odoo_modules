# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_create_bill = fields.Boolean(
        "Auto Create Vendor Bill", related='company_id.auto_create_bill', readonly=False)
    auto_validate_bill = fields.Boolean(
        "Auto Validate Vendor Bill", related='company_id.auto_validate_bill', readonly=False)
    auto_send_mail_bill = fields.Boolean(
        "Auto Send Mail Vendor Bill", related='company_id.auto_send_mail_bill', readonly=False)

    @api.onchange('auto_create_bill')
    def onchange_auto_create_bill(self):
        if not self.auto_create_bill and (self.auto_validate_bill or self.auto_send_mail_bill):
            self.auto_validate_bill = False
            self.auto_send_mail_bill = False