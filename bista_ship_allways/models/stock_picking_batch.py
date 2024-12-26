from odoo import models, fields, api


class StockPickingBatch(models.Model):
    _inherit = "stock.picking.batch"

    date_etd = fields.Date(string="ETD")
    date_eta = fields.Date(string="ETA")

    @api.depends('picking_ids', 'picking_ids.move_line_ids', 'picking_ids.move_ids', 'picking_ids.move_ids.state')
    def _compute_move_ids(self):
        super()._compute_move_ids()
        for batch in self:
            if batch.picking_type_code == "incoming":
                picking_with_container = next((picking for picking in batch.picking_ids if picking.container_id), None)
                if picking_with_container and picking_with_container.container_id == batch.name and picking_with_container.date_etd and picking_with_container.date_eta:
                    batch.date_etd = picking_with_container.date_etd
                    batch.date_eta = picking_with_container.date_eta
                elif picking_with_container:
                    data = picking_with_container._make_api_request(picking_with_container.container_id)
                    if data:
                        picking_with_container.date_eta = fields.Date.from_string(
                            data.get('eta')).isoformat() if data.get('eta') else False
                        picking_with_container.date_etd = fields.Date.from_string(
                            data.get('etd')).isoformat() if data.get('etd') else False
                        batch.date_eta = fields.Date.from_string(data.get('eta')).isoformat() if data.get(
                            'eta') else False
                        batch.date_etd = fields.Date.from_string(data.get('etd')).isoformat() if data.get(
                            'etd') else False
                    else:
                        batch.date_etd = False
                        batch.date_eta = False
                else:
                    batch.date_etd = False
                    batch.date_eta = False
