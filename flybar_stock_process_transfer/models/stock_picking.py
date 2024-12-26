# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import _, api, Command, fields, models
from odoo.osv import expression


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def process_transer(self):
        for picking_id in self:
            if picking_id.state not in ('cancel','done'):
                for move_line_id_without_package in picking_id.move_line_ids_without_package:
                    if move_line_id_without_package.qty_done == 0.0:
                        picking_id.action_set_quantities_to_reservation()
                picking_id.button_validate()


