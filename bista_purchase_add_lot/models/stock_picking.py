from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    component_location_id = fields.Many2one('stock.location', string="Component Location ID")

    def action_add_lot(self):
        subcontracting_id = self.purchase_id._get_subcontracting_resupplies() if self.purchase_id else False
        view_id = self.env.ref('bista_purchase_add_lot.view_stock_picking_add_lot_wizard_form').id
        return {
            'name': 'Add Lot',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking.add.lot.wizard',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_from_location_id': self.location_id.id,
                'default_location_id': self.location_dest_id.id,
                'default_component_location_id': subcontracting_id.location_dest_id.id},
        }
