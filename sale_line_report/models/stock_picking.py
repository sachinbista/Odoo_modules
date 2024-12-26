    # -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    picking_priority = fields.Integer(string="Priority",store=True)
