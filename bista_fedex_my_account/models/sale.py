# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    def _create_delivery_line(self, carrier, price_unit):
        res = super(SaleOrder, self)._create_delivery_line(carrier, price_unit)
        if carrier.delivery_type == 'fedex' and carrier.fedex_bill_my_account:
            res.name = '[FEDEX] Fedex Billing will remain to the customer'
        return res

    partner_fedex_carrier_account = fields.Char(copy=False, compute='_compute_fedex_carrier_account',
                                                inverse='_inverse_fedex_carrier_account', readonly=False,
                                                string="Fedex account number")
    fedex_bill_my_account = fields.Boolean(related='carrier_id.fedex_bill_my_account', readonly=True)

    @api.depends('partner_shipping_id')
    def _compute_fedex_carrier_account(self):
        for order in self:
            order.partner_fedex_carrier_account = order.partner_shipping_id.with_company(order.company_id).property_fedex_carrier_account

    def _inverse_fedex_carrier_account(self):
        for order in self:
            order.partner_shipping_id.with_company(order.company_id).property_fedex_carrier_account = order.partner_fedex_carrier_account

    def _action_confirm(self):
        if self.carrier_id.fedex_bill_my_account and not self.partner_fedex_carrier_account:
            raise UserError(_('You must enter an FEDEX account number.'))
        super(SaleOrder, self)._action_confirm()