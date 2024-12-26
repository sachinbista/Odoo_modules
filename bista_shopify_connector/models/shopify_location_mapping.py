##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2019 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class ShopifyLocationMapping(models.Model):
    _name = 'shopify.location.mapping'
    _description = 'Shopify Location Mapping'
    _rec_name = 'shopify_location_name'

    shopify_location_id = fields.Char(string="Shopify Location ID",
                                      help="Defines Shopify Location ID",
                                      required=True, copy=False)
    shopify_location_name = fields.Char(string="Shopify Location Name",
                                        help="Defines Shopify Location name",
                                        required=True, copy=False)
    odoo_location_id = fields.Many2one("stock.location",
                                       string="Location",
                                       help="Enter Odoo Location you want to map with shopify location",
                                       copy=False, store=True, compute="_compute_odoo_location")
    shopify_config_id = fields.Many2one('shopify.config', string="Shopify Configuration")
    shopify_legacy = fields.Boolean("Shopify Legacy", copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', copy=False, string="Warehouse")

    # @api.onchange('odoo_location_id')
    # def onchange_odoo_location_id(self):
    #     if self.odoo_location_id:
    #         self.odoo_location_id.is_shopify_location = True

    @api.depends('warehouse_id')
    def _compute_odoo_location(self):
        for rec in self:
            rec.odoo_location_id = False
            if rec.warehouse_id:
                rec.odoo_location_id = rec.warehouse_id.lot_stock_id.id
                rec.odoo_location_id.is_shopify_location = True
