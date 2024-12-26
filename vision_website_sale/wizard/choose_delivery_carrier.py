# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    def button_confirm(self):
        for order in self:
            # Add a delivery section line
            for line in order.order_id.order_line:
                existing_delivery_section = self.env['sale.order.line'].sudo().search([
                    ('order_id', '=', order.order_id.id),
                    ('name', '=', 'Delivery'),
                    ('display_type', '=', 'line_section')
                ], limit=1)
                if line.product_id.detailed_type == 'service' and len(
                        line.product_id.allowed_products.ids) > 0 and not existing_delivery_section:
                    self.env['sale.order.line'].create({
                        'order_id': order.order_id.id,
                        'name': 'Delivery',
                        'display_type': 'line_section',
                        'sequence': max(order.order_id.order_line.mapped('sequence')) + 1,
                    })

            # Add delivery products (you can customize the product_ids)
            self.order_id.set_delivery_line(self.carrier_id, self.delivery_price)
            self.order_id.write({
                'recompute_delivery_price': False,
                'delivery_message': self.delivery_message,
            })

            # self.env['sale.order.line'].create({
            #     'order_id': order.order_id.id,
            #     'product_id': self.carrier_id.product_id.id,
            #     'product_uom_qty': 1,
            #     'name': 'Delivery',
            # })
