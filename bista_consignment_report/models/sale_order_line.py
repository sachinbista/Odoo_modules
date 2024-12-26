# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line()
        consignment_account_id = self.env['ir.config_parameter'].sudo().get_param('bista_consignment_report.consignment_account_id')
        stock_move_line = self.env['stock.move.line'].search([('move_id.sale_line_id','=',self.id),('owner_id','!=',False),('product_id','=',self.product_id.id),('move_id.state','=','done')])
        
        for stock_move in stock_move_line.mapped('move_id').filtered(lambda s: s.consignment_stock_move):
            if consignment_account_id:
                res.update({
                    'account_id': consignment_account_id
                    })
        return res