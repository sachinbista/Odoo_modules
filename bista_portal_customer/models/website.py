# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _, _lt
from odoo.http import request

class Website(models.Model):
    _inherit = 'website'

    def default_confirm_order_message_without_payment(self):
        return _(
            "Your order is confirmed. Our team will soon check this order"
        )

    confirm_order_message_without_payment = fields.Char(
        string="Without Payment Message",
        translate=True,
        default=default_confirm_order_message_without_payment,
    )
    is_portal_customer = fields.Boolean(compute="_compute_is_portal_customer")

    def _compute_is_portal_customer(self):
        for rec in self:
            if request.session.uid:
                rec.is_portal_customer = request.env.user.is_portal_customer
            else:
                rec.is_portal_customer = False


    def _get_checkout_step_list(self):
        """ Return an ordered list of steps according to the current template rendered.

        :rtype: list
        :return: A list with the following structure:
            [
                [xmlid],
                {
                    'name': str,
                    'current_href': str,
                    'main_button': str,
                    'main_button_href': str,
                    'back_button': str,
                    'back_button_href': str
                }
            ]
        """
        self.ensure_one()
        is_extra_step_active = self.viewref('website_sale.extra_info').active
        redirect_to_sign_in = self.account_on_checkout == 'mandatory' and self.is_public_user()

        step_1_name = 'Review Order' if not self.is_portal_customer else 'Address'
        step_2_name = 'Payment' if not self.is_portal_customer else 'Confirm Checkout'

        steps = [(['website_sale.cart'], {
            'name': _lt("Review Order"),
            'current_href': '/shop/cart',
            'main_button': _lt("Sign In") if redirect_to_sign_in else _lt("Checkout"),
            'main_button_href': f'{"/web/login?redirect=" if redirect_to_sign_in else ""}/shop/checkout?express=1',
            'back_button':  _lt("Continue shopping"),
            'back_button_href': '/shop',
        }), (['website_sale.checkout', 'website_sale.address'], {
            'name': _lt(step_1_name),
            'current_href': '/shop/checkout',
            'main_button': _lt("Go to Confirm"),
            'main_button_href': f'{"/shop/extra_info" if is_extra_step_active else "/shop/confirm_order"}',
            'back_button':  _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        })]
        if is_extra_step_active:
            steps.append((['website_sale.extra_info'], {
                'name': _lt("Extra Info"),
                'current_href': '/shop/extra_info',
                'main_button': _lt("Continue checkout"),
                'main_button_href': '/shop/confirm_order',
                'back_button':  _lt("Return to shipping"),
                'back_button_href': '/shop/checkout',
            }))
        steps.append((['website_sale.payment'], {
            'name': _lt(step_2_name),
            'current_href': '/shop/payment',
            'back_button':  _lt("Back to cart"),
            'back_button_href': '/shop/cart',
        }))
        return steps

