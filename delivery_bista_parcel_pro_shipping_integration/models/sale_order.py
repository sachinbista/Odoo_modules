# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"


    parcel_pro_service_ids = fields.One2many('parcelpro.service','parcel_pro_service_id',string="Parcel Pro")
    insured_value = fields.Float(string="Insured Value")

    def action_confirm(self):
        res = super().action_confirm()
        delivery_lines = self.order_line.filtered(lambda line: line.product_id.default_code == 'Delivery_pro')
        for rec in self.picking_ids:
            rec.service_description = delivery_lines and delivery_lines[0].name or False
            rec.shipping_cost = delivery_lines and delivery_lines[0].price_unit or 0.0
        return res




