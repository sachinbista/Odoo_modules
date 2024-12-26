import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger('Shopify')


class Main(http.Controller):

    @http.route(['/shopify_odoo_webhook_for_order_create'], type='json', auth="public", methods=['POST'], csrf=False)
    def create_order_webhook(self, **kwargs):
        """ Using this controller we can create order in odoo"""
        res, shopify_config, webhook = self.get_info(
            route="shopify_odoo_webhook_for_order_create")
        if webhook.active:
            shopify_config.check_connection()
            request.env["sale.order"].sudo().shopify_import_orders_by_webhook(
                res, shopify_config)
            _logger.info("Started Process Of Creating Orders Via Webhook->:")

    @http.route('/shopify_odoo_webhook_for_customer_create', csrf=False, methods=['POST'], auth="public", type="json")
    def shopify_odoo_webhook_for_customer_create(self):
        """ Using this controller we can create customer in odoo"""
        res, shopify_config, webhook = self.get_info(
            "shopify_odoo_webhook_for_customer_create")
        if webhook.active:
            request.env['res.partner'].sudo(
            ).create_update_shopify_customers(res, shopify_config)
            _logger.info("Started Process Of Creating Customer Via Webhook->")

    @http.route('/shopify_odoo_webhook_for_customer_update', csrf=False, methods=['POST'], auth="public", type="json")
    def shopify_odoo_webhook_for_customer_update(self):
        """ Using this controller we can create customer in odoo"""
        res, shopify_config, webhook = self.get_info(
            "shopify_odoo_webhook_for_customer_update")
        if webhook.active:
            request.env['res.partner'].sudo(
            ).create_update_shopify_customers(res, shopify_config)
            _logger.info("Started Process Of Updating Customer Via Webhook->")

    @http.route('/shopify_odoo_webhook_for_product', csrf=False, methods=['POST'], auth="public", type="json")
    def shopify_odoo_webhook_for_product_create(self):
        """ Using this controller we can create product in odoo"""
        res, shopify_config, webhook = self.get_info(
            "shopify_odoo_webhook_for_product")
        if webhook.active:
            request.env['shopify.product.template'].sudo(
            ).create_update_shopify_product(res, shopify_config)
            _logger.info("Started Process Of Creating Products Via Webhook->")

    @http.route('/shopify_odoo_webhook_for_order_update', csrf=False, methods=['POST'], auth="public", type="json")
    def update_order_webhook(self):
        """ Using this controller we can update order in odoo"""
        res, shopify_config, webhook = self.get_info(
            "shopify_odoo_webhook_for_order_update")
        if webhook.active:
            shopify_config.check_connection()
            request.env["sale.order"].sudo().create_update_shopify_orders(
                res, shopify_config)
            request.env["sale.order"].sudo().process_return_order(
                res, shopify_config)
            request.env["account.move"].sudo(
            ).create_update_shopify_refund(res, shopify_config)
            _logger.info("Started Process Of Updating Orders Via Webhook->")

    def get_info(self, route):
        """ Using this method we can collect information related webhook"""
        res = request.get_json_data()
        host = "https://" + \
            request.httprequest.headers.get('X-Shopify-Shop-Domain')
        # url = "bistashopstore.myshopify.com"
        # host = "https://" + url
        shopify_config = request.env["shopify.config"].sudo().with_context(
            active_test=False).search([("shop_url", 'ilike', host)], limit=1)
        webhook = request.env['shopify.webhook'].sudo().search(
            [('callback_url', 'ilike', route), ('shopify_config_id', '=', shopify_config.id)], limit=1)
        return res, shopify_config, webhook
