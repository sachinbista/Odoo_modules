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

    @api.depends("goflow_store_id")
    def _compute_amazon_commission(self):
        for record in self:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            amazon_commission_rate = float(IrConfigParameter.get_param("commission.amazon_commission") or 0.0)
            amazon_stores = self.env['goflow.store'].search([('channel', 'ilike', 'amazon')]).ids or []
            if record.goflow_store_id and record.goflow_store_id.id in amazon_stores:
                record.amazon_commission = record.amount_total * amazon_commission_rate / 100

    amazon_commission = fields.Float('Amazon Commission', compute="_compute_amazon_commission", store=True)