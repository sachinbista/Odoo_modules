
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _,tools
from odoo.exceptions import UserError, ValidationError


class ProductCatalogMixin(models.AbstractModel):
    """ This mixin should be inherited when the model should be able to work
    with the product catalog.
    It assumes the model using this mixin has a O2M field where the products are added/removed and
    this field's co-related model should has a method named `_get_product_catalog_lines_data`.
    """
    _inherit = 'product.catalog.mixin'
    _description = 'Product Catalog Mixin'

    def action_add_from_catalog(self):
        kanban_view_id = self.env.ref('product.product_view_kanban_catalog').id
        search_view_id = self.env.ref('product.product_view_search_catalog').id
        tree_view_id = self.env.ref('bista_product_catalog_extension.product_view_tree_catalog').id
        additional_context = self._get_action_add_from_catalog_extra_context()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Products'),
            'res_model': 'product.product',
            'views': [(tree_view_id, 'tree'), (False, 'form')],
            'search_view_id': [search_view_id, 'search'],
            'domain': self._get_product_catalog_domain(),
            'context': {**self.env.context, **additional_context},
        }

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def add_catalog_lines(self,product_list,order_id):
        order = self.env['sale.order'].browse(order_id)
        old_lines = order.order_line
        for product_data in product_list:
            quantity = product_data['quantity']
            order.write({
                'order_line': [(0, 0, {
                    'product_id': product_data['product_id'],
                    'product_uom_qty': quantity,
                })]
            })
        (order.order_line - old_lines).mapped('product_id').write({'catalog_prd_quantity': 0})
        form_view = self.env.ref('sale.view_order_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'res_id':order_id,
            'views': [(False, 'form'), (False, 'tree')],
            'view_id': [form_view, 'form'],
            'view_mode': 'form',
            'target': 'current',
            'context': {},
        }
