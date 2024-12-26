# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError,UserError




class PosOrder(models.Model):
    _inherit = 'pos.order'

    def create_sales_order(self, partner_id, orderlines, cashier_id):
        res = super(PosOrder,self).create_sales_order(partner_id=partner_id, orderlines=orderlines, cashier_id=cashier_id)
        order = self.env['sale.order'].search([('name','=',res)])
        for dict_line in orderlines:
            for order_line in order.order_line:
                if order_line.product_id.id == dict_line['product']['id']:
                    is_special = dict_line['product'].get('is_special', False)
                    order_line.write({'is_special' : is_special})
        return res


    def refund(self):
        """Create a copy of order  for refund order"""
        refund_orders = self.env['pos.order']
        special_product_refund = self.env['ir.config_parameter'].sudo().get_param(
            'bista_special_order.bs_special_refund')
        for order in self:
            # When a refund is performed, we are creating it in a session having the same config as the original
            # order. It can be the same session, or if it has been closed the new one that has been opened.
            current_session = order.session_id.config_id.current_session_id
            if not current_session:
                raise UserError(_('To return product(s), you need to open a session in the POS %s', order.session_id.config_id.display_name))
            refund_order = order.copy(
                order._prepare_refund_values(current_session)
            )

            if special_product_refund ==False :
                orderline = order.lines.filtered(lambda s: not s.is_special)
            else:
                orderline = order.lines


            if orderline:
                for line in orderline:
                    PosOrderLineLot = self.env['pos.pack.operation.lot']
                    for pack_lot in line.pack_lot_ids:
                        PosOrderLineLot += pack_lot.copy()
                    line.copy(line._prepare_refund_data(refund_order, PosOrderLineLot))
                    refund_order._onchange_amount_all()
                refund_orders |= refund_order
            else:
                raise ValidationError(
                _("You are not allowed to create a Return For Special Products."))

        return {
            'name': _('Return Products'),
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': refund_orders.ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }