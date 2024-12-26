# -*- encoding: utf-8 -*-
##############################################################################
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
##############################################################################

from odoo import fields, models, api
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _default_picking_type(self):
        return self._get_picking_type(self.env.context.get('company_id') or self.env.company.id)

    delivery_type_id = fields.Many2one('stock.picking.type', string='Deliver Type',
                                       required=False, default=_default_picking_type,
                                       company_dependent=True,
                                       help="This will determine operation type of incoming shipment")

    @api.model
    def _get_picking_type(self, company_id):
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return picking_type[:1]
