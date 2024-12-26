# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def action_open_manufacturing_order(self):
        """
        Function creates package on product packaging on the confirmation of manufacturing order
        """
        res = super(MrpWorkorder, self).action_open_manufacturing_order()
        if self.product_id.is_package:
            sale_order_id = self.production_id.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
            if sale_order_id:
                package_sequence = self.env['ir.sequence'].next_by_code(
                            'stock.quant.package')
                today = fields.Datetime.now()
                package = self.env['stock.quant.package'].create({
                    'name': package_sequence,
                    'location_id': self.production_id.location_dest_id.id,
                    'sale_order_id': sale_order_id.id,
                    'customer_id': sale_order_id.partner_id.id
                    })
                self.production_id.finished_move_line_ids.write({'result_package_id': package.id})
        return res
