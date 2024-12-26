# -*- coding: utf-8 -*-
# Part of Bistasolutions. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from functools import partial


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pos_type_tax =  fields.Selection([
        ("no_tax", "No Tax"),
        ("wholesaler", "Wholesaler"),
        ("retailer", "Retailer")
    ], default='wholesaler', tracking=True,  string="Tax Type")


class POSSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        res = super(POSSession, self)._loader_params_product_product()
        res['search_params']['fields'].append('pos_type_tax')
        return res

    def _loader_params_res_partner(self):
        res = super(POSSession, self)._loader_params_res_partner()
        fields = res.get('search_params').get('fields')
        fields.extend(['customer_type'])
        res['search_params']['fields'] = fields
        return res



class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_type =fields.Selection([
        ("wholesaler", "Wholesaler"),
        ("retailer", "Retailer")
    ], default='wholesaler', tracking=True,  string="Customer Type")


class pos_order(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        res = super(pos_order, self)._order_fields(ui_order)
        partner_id = self.env['res.partner'].browse(ui_order.get('partner_id'))
        for line in res['lines']:
            product_id = self.env['product.product'].browse(line[2]['product_id'])
            if product_id.pos_type_tax =='no_tax' and 'tax_ids' in line[2]:
                line[2].update({'tax_ids':[]})
            elif product_id.pos_type_tax != partner_id.customer_type and 'tax_ids' in line[2]:
                line[2].update({'tax_ids':[]})
        return res