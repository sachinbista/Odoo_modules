# -*- coding: utf-8 -*-


from odoo import models, fields, api
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        ret = super(StockPicking, self).button_validate()
        if self.state == "done":
            for x in self.move_line_ids:
                if x.state == 'done' and x.lot_id:
                    x.lot_id.location_id = x.location_dest_id
        return ret

    def _get_fields_stock_barcode(self):
        """ List of fields on the stock.picking object that are needed by the
        client action. The purpose of this function is to be overridden in order
        to inject new fields to the client action.
        """
        res = super(StockPicking, self)._get_fields_stock_barcode()
        return res

    def action_assign(self):
        ret = super(StockPicking, self).action_assign()
        for x in self.move_line_ids:
            print(x.lot_id.name)
        return ret
