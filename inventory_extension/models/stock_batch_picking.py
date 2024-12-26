# -*- coding: utf-8 -*-

from odoo.addons.stock_picking_batch.models.stock_picking import StockPicking


def _package_move_lines(self, batch_pack=False):
    return super(StockPicking, self)._package_move_lines(batch_pack=batch_pack)

def button_validate(self):
    res = super(StockPicking, self).button_validate()
    to_assign_ids = set()
    if self and self.env.context.get('pickings_to_detach'):
        self.env['stock.picking'].browse(self.env.context['pickings_to_detach']).batch_id = False
        to_assign_ids.update(self.env.context['pickings_to_detach'])

    for picking in self:
        if picking.state != 'done':
            continue
        # Avoid inconsistencies in states of the same batch when validating a single picking in a batch.
        #Bhaviraj Code commented because the picking should not be null
        # if picking.batch_id and any(p.state != 'done' for p in picking.batch_id.picking_ids):
        #     picking.batch_id = None

        # If backorder were made, if auto-batch is enabled, seek a batch for each of them with the selected criterias.
        to_assign_ids.update(picking.backorder_ids.ids)

    # To avoid inconsistencies, all incorrect pickings must be removed before assigning backorder pickings
    assignable_pickings = self.env['stock.picking'].browse(to_assign_ids)
    for picking in assignable_pickings:
        picking._find_auto_batch()

    return res

StockPicking._package_move_lines = _package_move_lines
StockPicking.button_validate = button_validate
