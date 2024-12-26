# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def avg_landed_cost(self):
        landed_cost_ids = self.search([('state', '=', 'done')])
        for landed_cost_id in landed_cost_ids:
            for line in landed_cost_id.valuation_adjustment_lines:
                if line.additional_landed_cost and line.quantity:
                    self.env.cr.execute("""update stock_valuation_adjustment_lines set avg_landed_cost=%s where id=%s"""%((line.quantity/line.additional_landed_cost),line.id))


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    avg_landed_cost = fields.Monetary(string="Avg. Landed Cost")

    def write(self, vals):
        res = super(AdjustmentLines, self).write(vals)
        for line in self:
            if line.additional_landed_cost and line.quantity:
                self.env.cr.execute("""update stock_valuation_adjustment_lines set avg_landed_cost=%s where id=%s"""%((line.quantity/line.additional_landed_cost),line.id))
        return res 

