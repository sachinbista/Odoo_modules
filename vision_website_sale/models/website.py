# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    def _prepare_sale_order_values(self, partner_sudo):
        res = super()._prepare_sale_order_values(partner_sudo=partner_sudo)
        if partner_sudo.warehouse_id:
            res.update({'warehouse_id': partner_sudo.warehouse_id.id})
        return res

    def _get_product_available_qty(self, product):
        if self._context.get('partner_warehouse_id'):
            partner_id = self.env.user.partner_id
            res = product.with_context(warehouse=partner_id.warehouse_id.id).free_qty
            return res
        else:
            return product.with_context(warehouse=self._get_warehouse_available()).free_qty
