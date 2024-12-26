# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit="product.product"

    is_package = fields.Boolean(string="Is Package", default=False)
