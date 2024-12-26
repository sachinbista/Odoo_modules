# -*- coding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2012 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import tools
from odoo import api, fields, models


class ProductWarehouseQuantityReport(models.Model):
    _name = "product.warehouse.quantity.report"
    _description = "Product Warehouse Quantity Report"
    _auto = False

    product_id = fields.Many2one('product.product', 'Product Variant')
    default_code = fields.Char('Internal Reference', index=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    free_stock = fields.Float(string="On Hand Qty")
    avail_stock = fields.Float(string="Available Qty")
    reserve_qty = fields.Float(string="Reserve Qty")
    categ_id = fields.Many2one('product.category', 'Product Category',
                               readonly=True)
    uom_id = fields.Many2one('uom.uom', 'UOM', readonly=True)
    uom_name = fields.Char('UOM Name',  readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        all_products_ids = self.env['product.product'].sudo().search([(
            'sale_ok', '=', True), ('purchase_ok', '=', True)])
        all_warehouse_ids = self.env['stock.warehouse'].sudo().search([])
        query = """select 
                row_number() over (order by pp.id) as id, 
                pp.default_code as default_code, 
                sq.product_id as product_id,
                sw.id as warehouse_id, 
                sq.quantity AS free_stock,
                COALESCE((sq.quantity - sq.reserved_quantity), 0) AS avail_stock, 
                pt.categ_id as categ_id, 
                pt.uom_id as uom_id, 
                uom.name as uom_name, 
                sq.reserved_quantity as reserve_qty 
                from stock_quant sq
                inner join product_product pp on pp.id = sq.product_id
                inner join stock_location sl on sl.id = sq.location_id and sl.usage = 'internal' 
                inner join product_template pt on pt.id = pp.product_tmpl_id
                inner join product_category pc on pc.id = pt.categ_id
                inner join uom_uom uom on uom.id = pt.uom_id
                inner join stock_warehouse sw ON sw.id = sl.warehouse_id 
                where sq.product_id in """ + str(tuple(all_products_ids.ids)) + """ and 
                sw.id in """ + str(tuple(all_warehouse_ids.ids))
        result_query = """CREATE VIEW %s as (%s)""" % (
            self._table, query)
        self.env.cr.execute(result_query)
