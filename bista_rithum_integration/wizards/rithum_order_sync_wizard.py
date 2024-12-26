##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import fields, models


class RithumOrderSyncWizard(models.TransientModel):
    _name = 'rithum.order.sync.wizard'
    _description = 'Rithum order sync wizard'

    # message = fields.Char('Waring', default='Qty has been change in rithum order line, are you want to sync order to rithun.')
    message = fields.Char('warning', default='Qty has been changed in the Rithum order line, you have to change qty manually on the sale order line to sync the order.')

    def sync_rithum_order(self):
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        sale_id = picking.sale_id
        # code is un-comment if auto rithum order sync required on lines qty cancel
        # update_rithum_lines = self.env.context.get('updated_lines')
        picking.action_clear_quantities_to_zero()
        # for u_line in update_rithum_lines:
        #     rithum_product_id = self.env['rithum.product.product'].search(
        #         [('rithum_product_id', '=', u_line.get('sku'))], limit=1)
        #     order_line = sale_id.order_line.filtered(lambda o_line: o_line.product_id == rithum_product_id.product_id)
        #     order_line.product_uom_qty = u_line.get('acceptedQuantity')
        sale_id.rithum_warning_accepted = True
