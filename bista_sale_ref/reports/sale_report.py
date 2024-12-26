# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api

class SaleReport(models.Model):
    _inherit = "sale.report"

    sale_ref_id = fields.Many2one('res.partner', string="Sales Rep", domain=[('is_sale_ref', '=', True)])


    def _select_sale(self):
        select_ = super()._select_sale() + """
            ,
            s.sale_ref_id AS sale_ref_id
        """
        return select_

    def _group_by_sale(self):
        group_by = super()._group_by_sale() + """
            ,
            s.sale_ref_id
        """
        return group_by

