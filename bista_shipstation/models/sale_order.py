# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_pay = fields.Boolean('Delivery ShipStation Pay', store=True, copy=False, default=False)
    ss_quotation_carrier = fields.Char(string='Shipstation carrier code', )
    ss_quotation_service = fields.Char(string='Shipstation service code', )
    is_free_shipping = fields.Boolean('Is Free Shipping ??')
    ship_via = fields.Char('Ship Via',store=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for line in self:
            if line.partner_id:
                line.ship_via=line.partner_id.ship_via

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        order_confirm_hour = int(
            self.env['ir.config_parameter'].sudo().get_param('bista_shipstation.order_confirm_hour'))
        for order in self:
            if order_confirm_hour and not order.commitment_date:
                date_order = order.date_order + timedelta(hours=order_confirm_hour)
                order.write({'commitment_date': date_order})
        return res

    # def copy_data(self, default=None):
    #     if default is None:
    #         default = {}
    #         default['ship_via'] = self.ship_via
    #     return super(SaleOrder, self).copy_data(default)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    third_part_account = fields.Boolean('Third Party Shipping')
    bill_account = fields.Char('Account No')
    bill_postal_code = fields.Char('Postal Code')
    bill_country_code = fields.Many2one('res.country', string="Country")
    carrier_id = fields.Many2one('shipstation.delivery.carrier')
    service_id = fields.Many2one('shipstation.carrier.service')
    ship_via=fields.Char('Ship Via')
