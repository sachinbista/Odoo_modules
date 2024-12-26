##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import time
from odoo import models


class UpdateOrderStatus(models.TransientModel):

    _name = 'update.order.status'
    _description = 'Update Order Status'

    def update_order_status_in_shopify(self):
        picking_obj = self.env['stock.picking']
        if self._context.get('active_ids'):
            picking_ids = picking_obj.browse(self._context.get('active_ids'))
            for picking in picking_ids:
                picking.sale_id.shopify_update_order_status(picking.shopify_config_id,picking_ids=picking)
