from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        subcontracting_picking_ids = self._get_subcontracting_resupplies()
        for rec in subcontracting_picking_ids:
            subcontracting_location = rec.location_dest_id
            picking_id = self.picking_ids.filtered(lambda l: l.id != rec.id)
            if picking_id:
                picking_id.component_location_id = subcontracting_location.id
        return res
