# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process_cancel_backorder(self):
        """
            This function is added to Cancel respected Backorder of Dropship/Receipt related to Delivery.

            :return:
            @author: Ashish Ghadi @Bista Solutions Pvt. Ltd.
        """

        pickings_to_validate = self.env.context.get('button_validate_picking_ids')
        sale_id = self.env['sale.order'].search([('name', '=', self._context.get('default_origin'))], limit=1)
        po_id = self.env['purchase.order'].sudo().browse(sale_id.auto_purchase_order_id.id)
        po_picking_ids = po_id.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))

        if sale_id and sale_id.auto_generated:
            for po_picking_id in po_picking_ids:
                pickings_to_validate.append(po_picking_id.id)
        if pickings_to_validate:
            return self.env['stock.picking'].browse(pickings_to_validate) \
                .with_context(skip_backorder=True, picking_ids_not_to_backorder=pickings_to_validate)\
                .sudo().button_validate()

        return super(StockBackorderConfirmation, self).process_cancel_backorder()
