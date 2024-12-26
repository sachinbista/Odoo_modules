# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2020 (https://www.bistasolutions.com)
#
##############################################################################
from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        if not self.partner_id.use_partner_credit_limit:
            return super(SaleOrder, self).action_confirm()
        else:
            partner = self.partner_id
            if (partner.credit + self.amount_total) > partner.credit_limit:
                raise ValidationError(
                    _("This customer has an open balance ${} that is over their approved credit limit of ${}. "
                      "Inform the customer that they must make a payment to reduce their balance before "
                      "this sales order can be confirmed.").format(
                        (partner.credit + self.amount_total), partner.credit_limit))
            return super(SaleOrder, self).action_confirm()
