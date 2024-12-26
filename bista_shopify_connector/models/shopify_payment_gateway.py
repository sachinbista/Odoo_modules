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
    company_id = fields.Many2one('res.company', string='Company', help='Company', default=lambda self: self.env.company)
    pay_journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                     domain=[('type', 'in', ['cash', 'bank'])])
