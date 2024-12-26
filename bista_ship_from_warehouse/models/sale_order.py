# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self, fields):
        result = super(SaleOrder, self).default_get(fields)
        company_id = result.get('company_id')
        result['warehouse_id'] = self.env['stock.warehouse'].search([('is_default_warehouse', '=', True),('company_id', '=', company_id)], limit=1).id
        
        return result


    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True, tracking=True,
        compute='_compute_warehouse_id', store=True, readonly=False, precompute=True,
        states={'sale': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', False)]},
        check_company=True)

    
