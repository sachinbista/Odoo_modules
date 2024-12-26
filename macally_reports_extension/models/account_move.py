##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields
import re


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def product_name(self):
        result_string = ""
        for line in self:
            pattern = r"\[.*?\]"
            result_string = re.sub(pattern, "", line.name)
        return result_string



