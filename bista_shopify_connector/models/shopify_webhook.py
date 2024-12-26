from odoo import models, fields, api, _
from .. import shopify
from odoo.exceptions import ValidationError

class ShopifyWebhook(models.Model):

    _name = "shopify.webhook"
    _description = 'Shopify Webhook'

    active = fields.Boolean(default=False)
    webhook_name = fields.Char(string='Name')
    webhook_action = fields.Selection([('products/create', 'When Product is Create'),
                                       ('orders/create', 'When Order is Create'),
                                       ('customers/create', 'When Customer is Create'),
                                       ('orders/updated', 'When Order is Updated'),
                                       ('collections/updated',
                                        'When Collection is Updated')
                                       # ('inventory_levels/update','When Stock is Updated')
                                    ],help='Particular action for the webhook.')
    webhook_id = fields.Char('Webhook Id in Shopify')
    callback_url = fields.Text("CallBack URL")
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        copy=False,
                                        ondelete="cascade")
    
    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            available_webhook = self.search([
                ('shopify_config_id', '=', values.get('shopify_config_id')),
                ('webhook_action', '=', values.get('webhook_action')),
                ('active', '=', False)], limit=1)
            if available_webhook:
                raise ValidationError(_('Webhook is already created with the same action.'))
        return super(ShopifyWebhook, self).create(vals_list)

    def get_route(self):
        route = False
        webhook_action = self.webhook_action
        if webhook_action == 'products/create':
            route = "/shopify_odoo_webhook_for_product"
        elif webhook_action == 'orders/create':
            route = "/shopify_odoo_webhook_for_order_create"        
        elif webhook_action == 'customers/create':
            route = "/shopify_odoo_webhook_for_customer_create"
        elif webhook_action == 'orders/updated':
            route = "/shopify_odoo_webhook_for_order_update"
        elif webhook_action == 'collections/updated':
            route = "/shopify_odoo_webhook_for_collection_update"
        # elif webhook_action == 'inventory_levels/update':
        #     route = "/shopify_odoo_webhook_import_stock"
        return route

    # def get_webhook(self):
    #     shopify_config_id = self.shopify_config_id
    #     shopify_config_id.check_connection()
    #     route = self.get_route()
    #     current_url = shopify_config_id.shop_url
    #     shopify_webhook = shopify.Webhook()
    #     url = current_url + route
    #     if url[:url.find(":")] == 'http':
    #         raise Warning("Address protocol http:// is not supported while creating the webhook")
    #     responses = shopify_webhook.find()
    #     if responses:
    #         for response in responses:
    #             if response.topic == self.webhook_action:
    #                 self.write({"webhook_id": response.id, 'callback_url': response.address,'state': 'active'})
    #                 return True
    #     webhook_vals = {"topic": self.webhook_action, "address": url, "format": "json"}
    #     response = shopify_webhook.create(webhook_vals)
    #     if response.id:
    #         updated_webhook = response.to_dict()
    #         self.write({"webhook_id": updated_webhook.get("id"), 'callback_url': url, 'state': 'active'})
    #         return True