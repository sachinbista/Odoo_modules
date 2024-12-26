# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'


    def split_packages_count(self):
        form_view_id = self.env.ref('stock_picking_extend.stock_picking_extend_wizard_for_package')
        product_id = self.product_id.name
        product_quantity = self.move_id.product_uom_qty - self.move_id.quantity_done
        context = {
            'product_name': product_id,
            'product_quantity': product_quantity,

        }
        return {
            'name': 'Package Split',
            'type': 'ir.actions.act_window',
            'res_model': 'package.split.wizard',
            'view_mode': 'form',
            'view_id': form_view_id.id,
            'target': 'new',
            'context': context
        }