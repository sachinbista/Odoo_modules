##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError
import time


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        res = super()._post(soft)
        for rec in self:
            config_id = rec.sale_order_id.rithum_config_id
            if config_id:
                config_id.create_invoice_rithum_order(rec)
                # time.sleep(10)
                # if order_status == 'shipped':
                #     config_id.create_invoice_rithum_order(rec)
                # else:
                #     raise ValidationError(_("You can not post invoice without full delivery"))
        return res

    def _create_rithum_invoice_manualy(self):
        for rec in self:
            config_id = rec.sale_order_id.rithum_config_id
            if config_id:
                config_id.create_invoice_rithum_order(rec)
