import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger('Shopify')

class Main(http.Controller):

	@http.route(['/shopify_odoo_webhook_for_order_create'], type='json', auth="public", methods=['POST'],csrf=False)
	def create_order_webhook(self,**kwargs):
		res, shopify_config, webhook = self.get_info(route="shopify_odoo_webhook_for_order_create")
		_logger.info('Create OrderRes**************************: %s' % (res,))
		_logger.info('Create Order shopify_config**************************: %s' % (shopify_config,))
		_logger.info('Create Order wmethodsebhook**************************: %s' % (webhook,))
		if webhook.active:
			shopify_config.check_connection()
			request.env["sale.order"].sudo().create_update_shopify_orders(res, shopify_config)
			_logger.info("Started Process Of Creating Orders Via Webhook->:")
		else:
			_logger.info("No Webhook Found->")

	@http.route('/shopify_odoo_webhook_for_customer_create', csrf=False, methods=['POST'],auth="public", type="json")
	def shopify_odoo_webhook_for_customer_create(self):
		res, shopify_config, webhook = self.get_info("shopify_odoo_webhook_for_customer_create")
		_logger.info('Create Customer Res**************************: %s' % (res,))
		_logger.info('Create Customer shopify_config**************************: %s' % (shopify_config,))
		_logger.info('Create Customer webhook**************************: %s' % (webhook,))
		if webhook.active:
			request.env['res.partner'].sudo().create_update_shopify_customers(res,shopify_config)
			_logger.info("Started Process Of Creating Customer Via Webhook->")
		else:
			_logger.info("No Webhook Found->")

	@http.route('/shopify_odoo_webhook_for_product', csrf=False, methods=['POST'],auth="public", type="json")
	def shopify_odoo_webhook_for_product_create(self):
		res, shopify_config, webhook = self.get_info("shopify_odoo_webhook_for_product")
		_logger.info('Create Product Res**************************: %s' % (res,))
		_logger.info('Create Product shopify_config**************************: %s' % (shopify_config,))
		_logger.info('Create Product webhook**************************: %s' % (webhook,))
		if webhook.active:
			request.env['shopify.product.template'].sudo().create_update_shopify_product(res,shopify_config)
			_logger.info("Started Process Of Creating Products Via Webhook->")
		else:
			_logger.info("No Webhook Found->")

	@http.route('/shopify_odoo_webhook_for_order_update', csrf=False, methods=['POST'],auth="public", type="json")
	def update_order_webhook(self):
		res, shopify_config, webhook = self.get_info("shopify_odoo_webhook_for_order_update")
		_logger.info('Order Update**************************: %s' % (res,))
		_logger.info('Order Update**************************: %s' % (shopify_config,))
		_logger.info('Update Order webhook**************************: %s' % (webhook,))
		if webhook.active:
			shopify_config.check_connection()
			request.env["sale.order"].sudo().create_update_shopify_orders(res, shopify_config)
			_logger.info("Started Process Of Updating Orders Via Webhook->")
		else:
			_logger.info("No Webhook Found->")

	# @http.route('/shopify_odoo_webhook_import_stock', csrf=False, methods=['POST'],auth="public", type="json")
	# def import_stock_webhook(self):
	# 	res, shopify_config, webhook = self.get_info("shopify_odoo_webhook_import_stock")
	# 	_logger.info('Import Stock**************************: %s' % (res,))
	# 	_logger.info('Import Stock**************************: %s' % (shopify_config,))
	# 	_logger.info('Import Stock Webhook**************************: %s' % (webhook,))
	# 	if webhook.active:
	# 		request.env["shopify.product.template"].sudo().shopify_import_stock(shopify_config)
	# 		_logger.info("Started Process Of Importing Stock->")
	# 	else:
	# 		_logger.info("No Webhook Found->")

	def get_info(self, route):
		res = request.get_json_data()
		_logger.info('res**************************: %s' % (res,))
		_logger.info('res**************************: %s' % (request.httprequest.headers,))
		_logger.info('res**************************: %s' % (request.httprequest.headers,))
		host = "https://" + request.httprequest.headers.get('X-Shopify-Shop-Domain')
		# url = "bistashopstore.myshopify.com"
		# host = "https://" + url
		shopify_config = request.env["shopify.config"].sudo().with_context(active_test=False).search([("shop_url", 'ilike', host)], limit=1)
		webhook = request.env['shopify.webhook'].sudo().search([('callback_url', 'ilike', route),('shopify_config_id', '=', shopify_config.id)],limit=1)
		_logger.info("Get Info=====================->: %s" % (webhook,))
		return res, shopify_config, webhook