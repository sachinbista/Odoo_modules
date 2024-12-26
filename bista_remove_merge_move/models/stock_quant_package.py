# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    sale_order_id = fields.Many2one('sale.order', string="Sale Order Ref")
    customer_id = fields.Many2one('res.partner', string="Customer")
    barcode = fields.Char(string="Barcode")
    active = fields.Boolean("Active",default=True)

    @api.constrains('barcode')
    def _check_unique_barcode(self):
        barcode = self.with_context(active_test=False).search([('barcode', '=ilike', self.barcode)])
        barcode -= self
        if barcode:
            raise ValidationError(_('Barcode already exists with same Value - '
                                    '%s' % str(self.barcode)))

    def unpack(self):
        res = super(StockQuantPackage, self).unpack()
        if self.sale_order_id:
            self.sale_order_id = False
        if self.customer_id:
            self.customer_id = False
        if self.pack_date:
            self.pack_date = False
        return res
