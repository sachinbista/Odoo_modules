# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'
    _description = 'Delivery Carrier Selection Wizard'

    def _default_account_number(self):
        if 'default_carrier_id' in self._context:
            carrier_id = self.env['delivery.carrier'].browse(self._context.get('default_carrier_id'))
        else:
            carrier_id = self.carrier_id
        order_id = self.env['sale.order'].browse(self._context.get('default_order_id'))
        return  order_id.partner_id.property_ups_carrier_account if  carrier_id.delivery_type=='ups' else order_id.partner_id.property_fedex_carrier_account if  carrier_id.delivery_type=='fedex' else ''

    def _default_my_account(self):
        if 'default_carrier_id' in self._context:
            carrier_id = self.env['delivery.carrier'].browse(self._context.get('default_carrier_id'))
        else:
            carrier_id = self.carrier_id
        return self.carrier_id.ups_bill_my_account if carrier_id.delivery_type=='ups' else carrier_id.fedex_bill_my_account if carrier_id.delivery_type=='fedex' else ''

    bill_my_account = fields.Boolean("Bill My Account?", default=_default_my_account)
    account_number = fields.Char("Account Number",default=_default_account_number)

    def button_confirm(self):
        super(ChooseDeliveryCarrier, self).button_confirm()
        self.order_id.update({
            'partner_fedex_carrier_account': self.account_number if self.bill_my_account and self.carrier_id.delivery_type =='fedex' else '',
            'partner_ups_carrier_account': self.account_number if self.bill_my_account and self.carrier_id.delivery_type=='ups' else'',
            })


    @api.onchange('carrier_id')
    def onchange_account_bill(self):
        self.update({
            'bill_my_account': self.carrier_id.ups_bill_my_account if self.carrier_id.delivery_type=='ups' else self.carrier_id.fedex_bill_my_account if self.carrier_id.delivery_type=='fedex' else '',
            'account_number': self.order_id.partner_id.property_ups_carrier_account if  self.carrier_id.delivery_type=='ups' else self.order_id.partner_id.property_fedex_carrier_account if  self.carrier_id.delivery_type=='fedex' else ''
            })