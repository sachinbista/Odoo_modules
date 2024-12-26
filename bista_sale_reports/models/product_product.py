# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('standard_price')
    def _compute_std_price(self):
        for product in self:
            product.std_price = product.standard_price

    std_price = fields.Float(compute="_compute_std_price", store=True)

    def get_available_serial_numbers(self,date_from,date_to):
        quant = self.env['stock.quant'].search([('product_id','=',self.id),('lot_id','!=',False),('location_id.usage','=','customer')])
        result= []
        for lines in quant:
            if lines.lot_id:
                domain = [('product_id', '=', lines.product_id.id), '|',
                          ('location_id', '=', lines.location_id.id), ('location_dest_id', '=', lines.location_id.id),
                          ('lot_id', '=', lines.lot_id.id), '|', ('package_id', '=', lines.package_id.id),
                          ('result_package_id', '=', lines.package_id.id)]
                history_ids = self.env['stock.move.line'].search(domain)
                for qt in history_ids:
                    if qt.picking_id.picking_type_id.code == 'outgoing' and str(qt.picking_id.date_done) >=date_from and str(qt.picking_id.date_done) <=date_to :
                        result.append(lines.lot_id.id)

        result = self.Remove_Duplicates_List(result)
        return result

    def get_serial_numbers_sale_data(self,serial_id):

        quant = self.env['stock.quant'].search([('product_id','=',self.id),('lot_id','=',serial_id),('location_id.usage','=','customer')])
        result= []

        for lines in quant:
            if lines.lot_id:
                domain = [('product_id', '=', lines.product_id.id), '|',
                          ('location_id', '=', lines.location_id.id), ('location_dest_id', '=', lines.location_id.id),
                          ('lot_id', '=', lines.lot_id.id), '|', ('package_id', '=', lines.package_id.id),
                          ('result_package_id', '=', lines.package_id.id)]
                history_ids = self.env['stock.move.line'].search(domain)
                for qt in history_ids:

                    if qt.picking_id.picking_type_id.code == 'outgoing' :
                        result.append(lines.lot_id.name)
                        result.append(lines.value)
                        sale_order_line = self.env['sale.order.line'].search([('order_id', '=',qt.picking_id.sale_id.id),('product_id','=',self.id)],limit=1)

                        if sale_order_line:
                            result.append(sale_order_line[0].price_unit)
                        else:
                            result.append(1)
                        result.append(qt.owner_id)

        return result


    def Remove_Duplicates_List(self,res):
        final_list = []
        for num in res:
            if num not in final_list:
                final_list.append(num)
        return final_list


