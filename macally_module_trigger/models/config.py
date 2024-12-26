# -*- coding: utf-8 -*-

from odoo import fields, models, api


# automatic - enable configurations
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
