# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    def create_batch_picking_report_vals(self, sorted_move_lines):
        product_ids = sorted_move_lines.mapped('product_id')
        line_data_list = []
        for each_product in product_ids:
            line_ids = sorted_move_lines.filtered(lambda x: x.product_id.id == each_product.id)
            for each_rec in line_ids:
                line_data_dict = {'display_name': each_rec.display_name,
                                  'quantity': each_rec.quantity,
                                  'picking_display_name': each_rec.picking_id.display_name,
                                  'lot_id': each_rec.lot_id.name if each_rec.lot_id else False,
                                  'result_package_id': each_rec.result_package_id.name if each_rec.result_package_id else False,
                                  'barcode': each_rec.product_id.barcode if each_rec.product_id.barcode else False,
                                  'package_id': each_rec.package_id.name if each_rec.package_id else False}
                line_data_list.append(line_data_dict)

            line_data_list.append({'display_name': 'Total Quantity',
                                  'quantity': sum(line_ids.mapped('quantity')),
                                   'picking_display_name': '',
                                   'result_package_id': False,
                                   'barcode': False,
                                   'lot_id': False,
                                   'package_id': False})
        return line_data_list


