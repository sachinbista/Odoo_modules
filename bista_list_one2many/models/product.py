# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def action_product_warehouse_qty(self, product_id):
        product_id = product_id[0]
        res = []
        if product_id:
            prod_prod = self.env['product.product'].sudo().browse(product_id)
            warehouses = self.env['stock.warehouse'].sudo().search([])
            stock_quant_obj = self.env['stock.quant']
            for warehouse in warehouses:
                qty_available = prod_prod.with_context({'warehouse': warehouse.id}).qty_available
                # warehouse_stock_quant_qty = stock_quant_obj.sudo()._get_available_quantity(prod_prod, warehouse.lot_stock_id)
                if qty_available > 0:
                    res.append({
                        'warehouse': warehouse.code,
                        'qty': qty_available,
                        'uom': prod_prod.uom_id.name,
                        'so_available': warehouse.so_available,
                    })
            # To Sort the dictionary based on the Qty per branch.
            res = (sorted(res, key = lambda i: i['qty'],reverse=True))
        return res


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    so_available = fields.Boolean("SO Available")
