##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, _, api
import re


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    ship_via_id = fields.Many2one('ship.via', string='Ship Via')
    fob = fields.Char("FOB")
    vendor_payment_terms_id = fields.Many2one('vendor.payment.terms',
                                              string="Vendor Payment Term")

    @api.onchange('partner_id')
    def onchange_vendor_payment(self):
        if self.partner_id:
            for po in self:
                po.vendor_payment_terms_id = po.partner_id.vendor_payment_terms_id


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def product_name(self):
        result_string = ""
        for line in self:
            pattern = r"\[.*?\]"
            result_string = re.sub(pattern, "", line.name)
        return result_string
