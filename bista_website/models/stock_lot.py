from odoo import models, fields, api, _


class StockLot(models.Model):
    _inherit = 'stock.lot'

    available_quantity = fields.Float('Available Quantity', compute='_compute_available_quantity', store=True)

    @api.depends('quant_ids', 'quant_ids.quantity', 'quant_ids.reserved_quantity')
    def _compute_available_quantity(self):
        """
        Compute the available quantity of the lot.
        """
        for lot in self:
            # We only care for the quants in internal or transit locations.
            quants = lot.quant_ids.filtered(lambda q: q.location_id.usage in ['internal', 'transit'])
            available_qty = sum(quants.mapped('available_quantity'))
            lot.available_quantity = available_qty
    