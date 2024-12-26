# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    order_confirm_hour = fields.Char(string="Order Confirm Hour")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            order_confirm_hour=self.env['ir.config_parameter'].sudo().get_param('bista_shipstation.order_confirm_hour'))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('bista_shipstation.order_confirm_hour',
                                                         self.order_confirm_hour)
