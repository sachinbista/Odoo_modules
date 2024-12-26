# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _, tools


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    bs_special_refund = fields.Boolean(config_parameter='bista_special_order.bs_special_refund',
                                       related="pos_config_id.bs_special_refund", readonly=False)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    bs_special_refund = fields.Boolean(string="Special Product Refund", default=True)
