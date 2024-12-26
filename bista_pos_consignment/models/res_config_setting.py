# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, tools, _


class PosConfig(models.Model):
    _inherit = 'pos.config'
    _description = 'Point of Sale Configuration'

    pos_consignment_movement = fields.Boolean(help="Consignment Movement")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_consignment_movement = fields.Boolean(config_parameter='bista_pos_consignment.pos_consignment_movement',related="pos_config_id.pos_consignment_movement",readonly=False)