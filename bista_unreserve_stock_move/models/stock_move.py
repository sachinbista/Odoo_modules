# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context, OrderedSet
import inspect
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class StockMove(models.Model):
    _inherit = 'stock.move'
    origin_rule_id = fields.Many2one('stock.rule', 'Origin Stock Rule')

    def _search_picking_for_assignation(self):
        self.ensure_one()
        if not self.origin_rule_id.merge_move_to_picking:
            return False
        domain = self._search_picking_for_assignation_domain()
        picking = self.env['stock.picking'].search(domain, limit=1)
        return picking
    
    def do_unrserve(self):
        self._do_unreserve()


class StockRule(models.Model):
    _inherit = 'stock.rule'
    
    merge_move_to_picking = fields.Boolean(default=True)

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals['rule_id'] = self.id
        return new_move_vals
