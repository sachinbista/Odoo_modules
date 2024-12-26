# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        if self.partner_id and self.partner_id.lock_all_transaction:
            raise ValidationError(_("The customer has locked all transactions. You cannot validate this delivery."))
        return super(StockPicking, self).button_validate()
