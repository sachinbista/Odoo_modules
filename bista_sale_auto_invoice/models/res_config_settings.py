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

    auto_create_invoice = fields.Boolean(
        "Auto Create Customer Invoice", related='company_id.auto_create_invoice', readonly=False)
    auto_validate_invoice = fields.Boolean(
        "Auto Validate Customer Invoice", related='company_id.auto_validate_invoice', readonly=False)
    auto_send_mail_invoice = fields.Boolean(
        "Auto Send Mail Customer Invoice", related='company_id.auto_send_mail_invoice', readonly=False)

    @api.onchange('auto_create_invoice')
    def onchange_auto_create_invoice(self):
        if not self.auto_create_invoice and (self.auto_validate_invoice or self.auto_send_mail_invoice):
            self.auto_validate_invoice = False
            self.auto_send_mail_invoice = False
