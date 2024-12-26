# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order.line'

    is_gift_product = fields.Boolean('Is Gift Product', default=False)