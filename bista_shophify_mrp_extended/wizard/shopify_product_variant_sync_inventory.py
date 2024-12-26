##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, _



class ShopifyVariantInventorySync(models.TransientModel):
    _inherit = 'shopify.variant.inventory.sync'
    _description = 'Export Shopify Product Inventory'

    def get_available_qty(self, odoo_location, product, shopify_prod_search):
        bom_kits = self.env['mrp.bom']._bom_find(
            shopify_prod_search.mapped('product_variant_id'), bom_type='phantom')
        bom_product = [p.id for p in bom_kits]

        if bom_product and product.id in bom_product:
            available_qty = product.with_context({'location': odoo_location.id})._compute_quantities_dict(lot_id=False, owner_id=False, package_id=False)
            if available_qty:
                available_qty = available_qty.get(product.id).get('free_qty', 0.0) or 0.0
        else:
            available_qty = self.env['stock.quant']._get_quantity_with_child_locations(
                odoo_location, product)
        return available_qty

