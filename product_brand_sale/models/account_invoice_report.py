# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    brand_id = fields.Many2one('product.brand', string='Brand')

    def _select(self):
        res = super()._select()
        query = res.split('template.categ_id                                           AS product_categ_id,', 1)
        res = query[0] + 'template.categ_id as product_categ_id,template.brand_id as brand_id,' + query[1]
        return res

    def _group_by(self):
        res = super()._group_by()
        query = res.split('template.categ_id,', 1)
        res = query[0] + 'template.categ_id,template.brand_id,' + query[1]
        return res
