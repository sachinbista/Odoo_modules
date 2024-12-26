# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2016 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking'


    @api.onchange('product_return_moves')
    def onchange_product_return_moves(self):
        if not self.env.user.has_group(
                'bista_special_order.can_be_refund_special_order_group') and self.product_return_moves:
            self.product_return_moves = self.product_return_moves.filtered(
                lambda sm: sm.move_id and not sm.move_id.is_special)
            if not self.product_return_moves:
                raise UserError(_("No product to return (special product can not be returned)."))
