# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################
import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    rithum_config_id = fields.Many2one('rithum.config', string="Rithum Config ID", copy=False)
    rithum_carrier_id = fields.Char(string="Rihum Carrier ID", copy=False)
    rithum_shipping_method_id = fields.Char(string="Rihum Shipping Method ID", copy=False)
    rithum_warning_accepted = fields.Boolean("Rithum Warning Accepted", default=False, copy=False)

    def action_confirm(self):
        res = super().action_confirm()
        for rec in self:
            if rec.rithum_config_id and not rec._context.get('from_single') and not rec._context.get('from_auto_import'):
                rec.rithum_config_id.update_rithum_acknowledge_order(sale_ids=rec, config_id=rec.rithum_config_id)
        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        # note: that the code is un-comment if client requirement is to cancel order from odoo to rithum
        # if self.rithum_config_id:
            # order_id = self
            # self.rithum_config_id.cancel_rithum_order_status(sale_id=order_id)
        return res

    # @api.onchange('order_line')
    # def onchange_order_line(self):
    #     if self.rithum_config_id and not self.rithum_warning_accepted:
    #         self.rithum_warning_accepted = True
    #         return {
    #             'warning': {
    #                 'title': _("Warning for Rithum order sync"),
    #                 'message': "Please note that you have changes in order line that may create sync issue on rithum side"
    #             }
    #         }
