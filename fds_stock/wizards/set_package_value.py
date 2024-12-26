# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import fields, models


class SetPackgeValue(models.TransientModel):
    _name = 'set.package.value'
    _description = 'Set Package Value'

    picking_id = fields.Many2one('stock.picking', string='Picking', required=True)
    package_type_id = fields.Many2one('stock.package.type', string='Package Type')
    height = fields.Float('Height', help="Package Height")
    weight = fields.Float('Weight', help="Package Weight")
    depth = fields.Float('Depth', help='Package Depth')

    def action_confirm(self):
        self.picking_id.with_context(
            package_height=self.height,
            package_weight=self.weight,
            package_depth=self.depth,
            package_type_id=self.package_type_id and self.package_type_id.id or False
        ).action_put_in_pack()
