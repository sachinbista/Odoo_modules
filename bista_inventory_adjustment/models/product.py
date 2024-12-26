# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class ProductProduct(models.Model):
    _inherit="product.product"

    def action_lot_remove(self):
        """remove lot from quant for non-tracked products"""
        # Filter only non-tracked products from the recordset
        non_tracked_products = self.filtered(lambda p: p.tracking == 'none')
        if not non_tracked_products:
            return

        # Fetch quants for the selected products
        quants = self.env['stock.quant'].search([
            ('product_id', 'in', non_tracked_products.ids)
        ])

        if quants:
            # Update lot_id to False for all matched quants
            quants.write({'lot_id': False})
