# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.http import request


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def publish_products(self):
        for product in self:
            if not product.is_published:
                product.is_published = True
                product.website_published = True
  
    allowed_products = fields.Many2many(
        'product.product',
        'product_product_allowed_rel',
        'product_id',
        'allowed_product_id',
        string='Allowed Products'
    )
    allowed_customers = fields.Many2many(
        'res.partner',
        'product_template_customer_rel',
        'product_id',
        'customer_id',
        string='Allowed Customers'
    )

    is_group = fields.Boolean()

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        product_or_template = product_or_template.sudo()
        res.update({
            'product_type': product_or_template.type,
            'allow_out_of_stock_order': product_or_template.allow_out_of_stock_order,
            'available_threshold': product_or_template.available_threshold,
        })
        if product_or_template.is_product_variant:
            product = product_or_template
            partner_id = request.env['res.users'].browse(request.session.uid).partner_id
            free_qty = website.with_context(partner_warehouse_id=True)._get_product_available_qty(product)

            has_stock_notification = (
                    product._has_stock_notification(self.env.user.partner_id)
                    or request and product.id in request.session.get(
                'product_with_stock_notification_enabled', set())
            )
            stock_notification_email = request and request.session.get('stock_notification_email', '')
            res.update({
                'free_qty': free_qty,
                'cart_qty': product._get_cart_qty(website),
                'uom_name': product.uom_id.name,
                'uom_rounding': product.uom_id.rounding,
                'show_availability': product_or_template.show_availability,
                'out_of_stock_message': product_or_template.out_of_stock_message,
                'has_stock_notification': has_stock_notification,
                'stock_notification_email': stock_notification_email,
                'partner_id': partner_id,
            })
        else:
            res.update({
                'free_qty': 0,
                'cart_qty': 0,
            })
        return res

    def get_compatible_services(self, colors):
        product_template = self.env['product.product']
        colors = [int(color) for color in colors]
        variant_ids = self.product_variant_ids.filtered(
            lambda product: all (color in product.product_template_variant_value_ids.ids for color in colors))
        domain = [('detailed_type', '=', 'service'),
                  ('allowed_products', 'in', variant_ids.ids),
                  ('allowed_customers', 'in', self.env.user.partner_id.id)]
        return {'currency': self.env.company.currency_id.read(['id', 'name', 'symbol'])[0],
                'list': product_template.sudo().search_read(domain, ['id', 'display_name', 'list_price'])}


class Product(models.Model):
    _inherit = 'product.product'

    def _is_add_to_cart_allowed(self):
        tmpl = self.product_tmpl_id
        is_complementary = tmpl.detailed_type == 'service' and tmpl.is_group
        if is_complementary:
            return self.user_has_groups('base.group_system') or (
                    self.active and self.sale_ok and (self.website_published or is_complementary))
        return super()._is_add_to_cart_allowed()
