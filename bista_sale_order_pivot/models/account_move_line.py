# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    customer_po = fields.Char(string="Customer PO",
                              related='move_id.sale_order_id.customer_po',
                              store=True)
