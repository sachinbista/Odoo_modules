# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _


class ProductCategory(models.Model):
    _inherit = 'product.category'

    hide_category = fields.Boolean(string="Hide Category", company_dependent=True)
