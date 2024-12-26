# -*- coding: utf-8 -*-
from odoo import api, models, fields


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    fiscal_position_id = fields.Many2one('account.fiscal.position')


