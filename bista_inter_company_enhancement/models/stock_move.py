# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models,api,_,fields
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockMove, self).create(vals_list)
        return res

    @api.onchange('move_line_ids')
    def _onchange_move_line(self):
        """
            Added restriction on Detailed Ope line

            :return:
            @author: Daud Akhtar @Bista Solutions Pvt. Ltd.
        """
        if self.move_line_ids:
            updated_data = dict(self._context)
            if (self.picking_id.bs_is_inter_record and self.state != 'cancel' and not updated_data.get(
                    'allow_edit') == True) or (
                    self.picking_id.bs_is_inter_record and 'allow_edit' not in updated_data and self.state != 'cancel'):
                raise UserError("You cannot change anything from DS Line. Hints : Cancel SO --> Reset to draft ")
