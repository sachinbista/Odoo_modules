# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for order in self:
            if order.partner_id.lock_all_transaction:
                raise ValidationError(
                    _("The customer has locked all transactions. You cannot confirm this sale order."))
        return super(SaleOrder, self).action_confirm()