# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def send_to_shipper(self):
        if self.external_origin !='go_flow':
            return super(StockPicking, self).send_to_shipper()