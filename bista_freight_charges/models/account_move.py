# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    freight_charges = fields.Float('Freight Charges', compute="_compute_freight_charges", store=True)

    @api.depends("invoice_line_ids")
    def _compute_freight_charges(self):
        for record in self:
            freight_charges = 0.0
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            freight_product = int(IrConfigParameter.get_param("bista_freight_charges.freight_product")) or False
            freight_charge_lines = record.invoice_line_ids.filtered(lambda line: line.product_id.id == freight_product)
            if freight_charge_lines:
                freight_charges = sum(freight_charge_lines.mapped('price_subtotal')) or 0.0
            record.freight_charges = freight_charges
