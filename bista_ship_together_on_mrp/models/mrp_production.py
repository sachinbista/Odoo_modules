# -*- coding: utf-8 -*-
from odoo import api, models, fields


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    ship_together = fields.Html(compute="_get_so_ship_together", store=True)

    @api.depends('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ship_together')
    def _get_so_ship_together(self):
        for production in self:
            sale_orders = production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
            ship_together = ""
            for so in sale_orders.filtered(lambda x: x.ship_together):
                ship_together += f"""
                <p style='margin-bottom: 0'>
                <strong><a href='/web#model=sale.order&id={so.id}&view_type=form'>{so.display_name}</a></strong>:
                <span>{so.ship_together}</span></p>"""
            production.ship_together = ship_together
