##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class ShopifyPaymentGateway(models.Model):
    _name = 'shopify.payment.gateway'
    _description = "Shopify Payment Gateway"

    name = fields.Char("Name")
    code = fields.Char("Code", copy=False)
    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    pay_journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                     domain=[('type', 'in', ['cash', 'bank'])])
    in_pay_method_id = fields.Many2one('account.payment.method',
                                       string="Payment Method",
                                       domain=[('payment_type', '=', 'inbound')])
