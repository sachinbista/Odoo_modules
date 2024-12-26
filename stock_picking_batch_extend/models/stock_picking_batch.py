from odoo import models, fields, api


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    def _is_picking_auto_mergeable(self, picking):
        """ Verifies if a picking can be safely inserted into the batch without violating auto_batch_constrains.
        """
        res = super()._is_picking_auto_mergeable(picking)
        if (
                self.picking_type_id.batch_lock_in_progress
                and self.state == 'in_progress'
                and any(line.qty_done for line in self.move_line_ids)
        ):

            res = False
        return res

    def _sanity_check(self):
        erroneous_pickings = [
            x.id for x in self if not x.picking_ids <= x.allowed_picking_ids
        ]
        if erroneous_pickings:
            pass

