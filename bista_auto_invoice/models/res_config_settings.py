# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_failure_channel = fields.Many2one('discuss.channel',  config_parameter="bista_auto_invoice.payment_failure_channel",string="Payment Failure channel", readonly=False)
