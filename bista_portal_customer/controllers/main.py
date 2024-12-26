# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import fields, http, _
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteSaleInherit(WebsiteSale):

    def _get_shop_payment_values(self, order, **kwargs):
        res = super()._get_shop_payment_values(order, **kwargs)
        if request.env.user.is_portal_customer:
            res['submit_button_2_label'] = _("Confirm order")
        return res

    # @http.route()
    def shop_payment_get_status(self, sale_order_id, **post):
        # When skip payment step, the transaction not exists so only render
        # the waiting message in ajax json call
        if not request.website.is_portal_customer:
            return super().shop_payment_get_status(sale_order_id, **post)
        return {
            "recall": True,
            "message": request.website._render(
                "bista_portal_customer.order_state_message"
            ),
        }

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        if not request.website.is_portal_customer or not sale_order_id:
            return super().shop_payment_confirmation(**post)
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            is_portal_customer = request.env.user.is_portal_customer
            if is_portal_customer and not order.is_web_order:
                order.is_web_order = True
            values = self._prepare_shop_payment_confirmation_values(order)
            values['is_portal_customer'] = is_portal_customer
            return request.render("website_sale.confirmation", values)
        else:
            return request.redirect('/shop')

    def checkout_values(self, order, **kw):
        values = super(WebsiteSaleInherit, self).checkout_values(order, **kw)
        values['is_portal_customer'] = request.env.user.is_portal_customer
        return values
    
    @http.route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.provider. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.provider website but closed the tab without
           paying / canceling
        """
        order = request.website.sale_get_order()

        if order and not order.only_services and (request.httprequest.method == 'POST' or not order.carrier_id):
            # Update order's carrier_id (will be the one of the partner if not defined)
            # If a carrier_id is (re)defined, redirect to "/shop/payment" (GET method to avoid infinite loop)
            carrier_id = post.get('carrier_id')
            keep_carrier = post.get('keep_carrier', False)
            if keep_carrier:
                keep_carrier = bool(int(keep_carrier))
            if carrier_id:
                carrier_id = int(carrier_id)
            order._check_carrier_quotation(force_carrier_id=carrier_id, keep_carrier=keep_carrier)
            if carrier_id:
                return request.redirect("/shop/payment")

        redirection = self.checkout_redirection(order) or self.checkout_check_address(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False
        render_values['is_portal_customer'] = request.env.user.is_portal_customer

        if render_values['errors']:
            render_values.pop('payment_methods_sudo', '')
            render_values.pop('tokens_sudo', '')

        return request.render("website_sale.payment", render_values)

    @http.route(['/shop/cart'], type='http', auth="public", website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        """
        Main cart management + abandoned cart revival
        access_token: Abandoned cart SO access token
        revive: Revival method when abandoned cart. Can be 'merge' or 'squash'
        """
        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        if order and order.carrier_id:
            # Express checkout is based on the amout of the sale order. If there is already a
            # delivery line, Express Checkout form will display and compute the price of the
            # delivery two times (One already computed in the total amount of the SO and one added
            # in the form while selecting the delivery carrier)
            order._remove_delivery_line()

        request.session['website_sale_cart_quantity'] = order.cart_quantity

        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                raise NotFound()
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive == 'squash' or (revive == 'merge' and not request.session.get('sale_order_id')):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session.get('sale_order_id'):  # abandoned cart found, user have to choose what to do
                values.update({'access_token': abandoned_order.access_token})

        values.update({
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': [],
            'is_portal_customer': request.env.user.is_portal_customer,
        })
        if order:
            order.order_line.filtered(lambda l: l.product_id and not l.product_id.active).unlink()
            values['suggested_products'] = order._cart_accessories()
            values.update(self._get_express_shop_payment_values(order))

        values.update(self._cart_values(**post))
        return request.render("website_sale.cart", values)
