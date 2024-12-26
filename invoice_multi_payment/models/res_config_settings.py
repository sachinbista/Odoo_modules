# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    invoice_discount_account_id = fields.Many2one(
        'account.account', string='Invoice Discount')
    invoice_writeoff_account_id = fields.Many2one(
        'account.account', string='Write-Off')
    invoice_sale_tax_account_id = fields.Many2one(
        'account.account', string='Sale Tax')
    carry_forward_account_id = fields.Many2one(
        'account.account', string='Carry Forward Account')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_discount_account_id = fields.Many2one(
        related='company_id.invoice_discount_account_id',
        string='Discount Account',
        readonly=False)

    invoice_writeoff_account_id = fields.Many2one(
        related='company_id.invoice_writeoff_account_id',
        string='Write-Off Account',
        readonly=False)
    invoice_sale_tax_account_id = fields.Many2one(
        related='company_id.invoice_sale_tax_account_id',
        string='Sale Tax',
        readonly=False)
    carry_forward_account_id = fields.Many2one(
        related='company_id.carry_forward_account_id',
        string='Carry Forward Account',
        readonly=False)

