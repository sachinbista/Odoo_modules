# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_inventory_volume = fields.Char(string='Dimension Volume',
                                           config_parameter='sale_stock_extend.product_inventory_volume')

