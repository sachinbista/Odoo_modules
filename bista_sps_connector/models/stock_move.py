# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_new_picking_values(self):
        """
        Override the function to update the EDI config and outbound path.
        @return:
        @rtype:
        """
        picking_vals = super(StockMove, self)._get_new_picking_values()
        if self.mapped('group_id'):
            sale_id = self.mapped('group_id')[0].sale_id
            if sale_id:
                if sale_id.edi_config_id:
                    picking_vals.update(
                        {'edi_config_id': sale_id.edi_config_id.id})
                elif sale_id.partner_invoice_id and \
                        sale_id.partner_invoice_id.edi_config_id:
                    picking_vals.update(
                        {'edi_config_id': sale_id.partner_invoice_id.edi_config_id.id})

                if sale_id.edi_outbound_file_path:
                    picking_vals.update(
                        {'edi_outbound_file_path': sale_id.edi_outbound_file_path})
                elif sale_id.partner_invoice_id and \
                        sale_id.partner_invoice_id.edi_outbound_file_path:
                    picking_vals.update({
                        'edi_outbound_file_path': sale_id.partner_invoice_id.edi_outbound_file_path})
        return picking_vals
