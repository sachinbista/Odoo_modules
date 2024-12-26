from odoo import fields, models, api, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        res = super(StockMoveLine, self).create(vals_list)
        for rec in res:
            for bom in rec.product_id.bom_ids:
                if bom.type == 'subcontract':
                    if rec.picking_id and rec.picking_id.component_location_id and not self.env.context.get('is_scrap'):
                        rec.location_id = rec.picking_id.component_location_id.id
        return res
