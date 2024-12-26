# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions
# Copyright (C) 2020(http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models


# class ProductCategory(models.Model):
#     _inherit = "product.category"
#
#     short_code = fields.Char(string="Short Code")


class ProductCategory(models.Model):
    _inherit = "product.category"

    short_code = fields.Char(string="Short Code")

