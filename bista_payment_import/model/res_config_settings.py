# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bs_register_payment_discount_account_id = fields.Many2one('account.account',string='Import Payment Discount Account')
    bs_register_payment_writeoff_account_id = fields.Many2one('account.account',string='Import Payment Write-Off Account')
    bs_register_payment_income_account_id = fields.Many2one('account.account',string='Import Payment Income Account')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        params = self.env['ir.config_parameter'].sudo()
        bs_register_payment_discount_account_id = params.get_param('bs_register_payment_discount_account_id', default=False)
        bs_register_payment_writeoff_account_id = params.get_param('bs_register_payment_writeoff_account_id', default=False)
        bs_register_payment_income_account_id = params.get_param('bs_register_payment_income_account_id', default=False)
        res.update(
            bs_register_payment_discount_account_id=int(bs_register_payment_discount_account_id),
            bs_register_payment_writeoff_account_id=int(bs_register_payment_writeoff_account_id),
            bs_register_payment_income_account_id=int(bs_register_payment_income_account_id),
        )
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("bs_register_payment_discount_account_id", self.bs_register_payment_discount_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param("bs_register_payment_writeoff_account_id", self.bs_register_payment_writeoff_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param("bs_register_payment_income_account_id", self.bs_register_payment_income_account_id.id)