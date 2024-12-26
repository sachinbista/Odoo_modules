# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _


class QualityCheck(models.Model):
    _inherit = "quality.check"

    @api.depends('move_line_id.qty_done')
    def _compute_qty_line(self):
        super(QualityCheck, self)._compute_qty_line()
        for qc in self:
            if qc.move_line_id.qty_done > 1 and qc.move_line_id.product_id.tracking in ('none' , 'lot') and qc.measure_on=='move_line':
                qc.qty_line = 1
            else:
                qc.qty_line = qc.move_line_id.qty_done