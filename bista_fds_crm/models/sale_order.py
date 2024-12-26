# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def default_get(self, fields_list):
        ret = super(SaleOrder, self).default_get(fields_list)
        user_warehouse = self.env.user.property_warehouse_id
        if user_warehouse:
            ret.update({
                'warehouse_id': user_warehouse.id
            })
        return ret

    @api.onchange('warehouse_id', 'partner_id')
    def _onchange_get_fiscal_position(self):
        warehouse = self.warehouse_id
        partner = self.partner_id
        fsc_warehouse = warehouse.fiscal_position_id if warehouse else False
        fsc_partner = partner.property_account_position_id if partner else False
        self.fiscal_position_id = fsc_partner or fsc_warehouse



class StockRule(models.Model):
    """ A rule describe what a procurement should do; produce, buy, move, ... """
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        ''' Returns a dictionary of values that will be used to create a stock move from a procurement.
        This function assumes that the given procurement has a rule (action == 'pull' or 'pull_push') set on it.

        :param procurement: browse record
        :rtype: dictionary
        '''
        description_new = ''
        if 'sale_line_id' in values:
            description_new = self.env['sale.order.line'].browse(values.get('sale_line_id', False)).name
        elif 'move_dest_ids' in values:
            description_new = values.get('move_dest_ids')[0].description_picking
            
        res = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values)
        res['description_picking'] = description_new or res['description_picking']
        return res

    