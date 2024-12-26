# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    """
    Inherit a Product Template"
    """
    _inherit = "product.template"

    inventory_adjustment_date = fields.Datetime(string="Last Counted Date")


class ProductProduct(models.Model):
    """
    Inherit a Product Variant"
    """
    _inherit = "product.product"

    inventory_adjustment_date = fields.Datetime(string="Last Counted Date")
