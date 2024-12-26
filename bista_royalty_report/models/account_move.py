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

    @api.depends('invoice_line_ids', 'amount_total')
    def _compute_royalty_total(self):
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        amazon_commission_rate = float(IrConfigParameter.get_param("commission.amazon_commission") or 0.0)
        amazon_stores = self.env['goflow.store'].search([('channel', 'ilike', 'amazon')]).ids

        for invoice in self.filtered(lambda inv: inv.move_type == 'out_invoice'):
            royalty_amount = 0.0
            potential_royalty_amt = invoice.amount_total - invoice.freight_charges

            if invoice.goflow_store_id and invoice.goflow_store_id.id in amazon_stores:
                potential_royalty_amt -= (invoice.amount_total * amazon_commission_rate / 100)

            for invoice_line in invoice.invoice_line_ids.filtered(
                    lambda line: line.product_id.detailed_type == 'product'):
                royalty_lines = invoice_line.product_id.product_royalty_list.filtered(
                    lambda line: line.is_dropship == invoice_line.is_dropship)
                if royalty_lines:
                    for royalty_line in royalty_lines:
                        royalty_amount += potential_royalty_amt * royalty_line.royalty_id.royalty_percentage / 100
            invoice.royalty_amt = royalty_amount

    royalty_amt = fields.Float(string="Royalty", compute="_compute_royalty_total", store=True)
