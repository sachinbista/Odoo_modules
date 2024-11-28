##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import json
import requests
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import pandas as pd
import numpy as np
import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    shopify_product_product_ids = fields.One2many(
        "shopify.product.product",
        "product_variant_id",
        "Shopify Product Variants",
        help="Enter Shopify Product Variants")
    shopify_shipping_product = fields.Boolean(
        "Is Shopify Shipping Product",
        help="Use this product as shipping product while import order?",
        tracking=True)
    shopify_discount_product = fields.Boolean(
        "Is Shopify Discount Product",
        help="Use this product as discount product while import order?",
        tracking=True)
    is_gift_card = fields.Boolean("Is Gift Card?")
    shopify_name = fields.Char("Shopify Name")

    # @api.constrains('default_code')
    # def _check_default_code_uniq_product(self):
    #     """
    #     Prevent the default code duplication when creating product variant
    #     """
    #     for rec in self:
    #         if rec.default_code:
    #             search_product_count = self.search_count(
    #                 [('default_code', '=', rec.default_code), ('id', '!=', rec.id)])
    #             if search_product_count > 1:
    #                 raise ValidationError(_(f'SKU Code "{rec.default_code}" must be unique per Product.'))
    #     return True

    @api.model_create_multi
    def create(self, vals):
        """
            Restrict a user from creating multiple shipping products and multiple
            discount products for Shopify.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        for val in vals:
            res = super(ProductProduct, self).create(val)
            shopify_shipping_product = val.get('shopify_shipping_product') or \
                self.shopify_shipping_product
            shopify_discount_product = val.get('shopify_discount_product') or \
                self.shopify_discount_product
            if shopify_shipping_product:
                shipping_product_variant_count = self.search_count(
                    [('type', '=', 'service'),
                     ('shopify_shipping_product', '=', True)])
                if shipping_product_variant_count > 1:
                    raise ValidationError(_("Shipping Product Already Exists in "
                                            "the system !"))
            if shopify_discount_product:
                discount_product_variant_count = self.search_count(
                    [('type', '=', 'service'),
                     ('shopify_discount_product', '=', True)])
                if discount_product_variant_count > 1:
                    raise ValidationError(_("Discount Product Already Exists in "
                                            "the system !"))
        return res

    def write(self, vals):
        """
            Restrict a user from creating multiple shipping products and multiple
            discount products for Shopify.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        res = super(ProductProduct, self).write(vals)
        shopify_product_obj = self.env['shopify.product.product']
        for rec in self:
            shopify_shipping_product = vals.get('shopify_shipping_product') or \
                rec.shopify_shipping_product
            shopify_discount_product = vals.get('shopify_discount_product') or \
                rec.shopify_discount_product
            if shopify_shipping_product:
                shipping_product_variant_count = self.search_count(
                    [('type', '=', 'service'),
                     ('shopify_shipping_product', '=', True)])
                if shipping_product_variant_count > 1:
                    raise ValidationError(_("Shipping Product Already Exists in "
                                            "the system !"))
            if shopify_discount_product:
                discount_product_variant_count = self.search_count(
                    [('type', '=', 'service'),
                     ('shopify_discount_product', '=', True)])
                if discount_product_variant_count > 1:
                    raise ValidationError(_("Discount Product Already Exists in "
                                            "the system !"))
            shopify_products = shopify_product_obj.search(
                [('product_variant_id', '=', rec.id)])
            if shopify_products:
                shopify_products.filtered(lambda p: p.shopify_inventory_item_id).update(
                    {'lst_price': rec.lst_price,
                     'barcode': rec.barcode or False,
                     'weight': rec.weight or False, })
        return res

    def split_graphql_data_into_batches(self,input_list, batch_size):
        """
            Using this method spliting the bunch of data in chunks/batches
        """
        for data in range(0, len(input_list), batch_size):
            yield input_list[data:data + batch_size]

    def inventory_update_using_server_action(self, rec):
        """
            Using this method updating bulk of stock by mutation.
        """
        shopify_config = self.env['shopify.config']
        shopify_config_id = shopify_config.search([('state','=', 'success')],limit=1)
        graphql_url = shopify_config_id.graphql_url
        token = shopify_config_id.password
        user = self.env.user
        if not graphql_url:
            raise UserError(_("GraphQL URL is missing, Please enter a GraphQL URL"))
        if not token:
            raise UserError(_("Access token is missing, Please check."))
        try :
            url, access_token = graphql_url,token
            headers = {
                      "Content-Type": "application/json",
                      "X-Shopify-Access-Token": access_token
                    }

            mutation = """
            mutation inventorySetOnHandQuantities($input: InventorySetOnHandQuantitiesInput!) {
                inventorySetOnHandQuantities(input: $input) {
                  userErrors {
                    field
                    message
                  }
                  inventoryAdjustmentGroup {
                    createdAt
                    reason
                    changes {
                      name
                      delta
                    }
                  }
                }
            }
            """
            graphql_data, location_id = self.prepare_graphql_data_update_inventory_server_action(rec)
            batch_size = 100
            graphql_batched_data = list(self.split_graphql_data_into_batches(graphql_data, batch_size))
            for index, graphql_batch in enumerate(graphql_batched_data):
                graphql_dataframe = pd.DataFrame(graphql_batch)
                for index, row in graphql_dataframe.iterrows():
                    qty = row['available_qty']
                    variables = {
                                "input": {
                                "reason": "correction",
                                "setQuantities": {
                                        "inventoryItemId":"gid://shopify/InventoryItem/"+ row['inventory_item_id'],
                                        "locationId": "gid://shopify/Location/"+location_id.shopify_location_id,
                                        "quantity":row['available_qty']
                                    }
                                }
                            }
                    try:
                        data = {"query": mutation, "variables": variables}
                        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
                        self.message_post(body=f"Inventory is updated in shopify by {user.name}, quantity is {qty}")
                        _logger.info(response)
                    except Exception as e:
                        raise UserError(e)
        except Exception as e:
            raise UserError(e)

    def prepare_graphql_data_update_inventory_server_action(self,rec):
        """
            Using this mehtod preparing data of variables in bulk"
        """
        stock_quant_obj = self.env['stock.quant'].sudo()
        shopify_prod_obj = self.env['shopify.product.product'].sudo()
        shopify_config = self.env['shopify.config'].sudo()
        stock_location = self.env['stock.location'].sudo()
        graph_data = []

        shopify_config_rec = shopify_config.search([('state','=','success')], limit=1)
        # active_ids = self._context.get('active_ids')
        # if active_ids and shopify_config_rec:
        if  rec and shopify_config_rec:
            product_ids = rec
            for product_id in product_ids:
                product_count = shopify_prod_obj.with_user(self.env.user).search_count([
                    ('product_variant_id', '=', product_id.id),
                    ('shopify_product_id', 'not in', ('', False))
                ])
                if product_count == 0:
                    raise UserError("Please make sure product exist in shopify.")
                else:
                    available_qty = 0
                    quants = stock_quant_obj.with_user(self.env.user).search(
                            [('on_hand', '=', True),
                            ('product_id', '=',product_id.id)])
                    location_id = stock_location.search([], limit=1)
                    available_qty = sum(quants.mapped('available_quantity'))
                    shopify_product = shopify_prod_obj.with_user(self.env.user).search([
                            ('product_variant_id', '=', product_id.id),
                            ('shopify_config_id', '=',
                             shopify_config_rec.id)], limit=1)
                    inventory_item_id = shopify_product.shopify_inventory_item_id
                    update_shopify_inv = shopify_product.update_shopify_inv
                    if inventory_item_id and update_shopify_inv:
                        graph_data.append({'inventory_item_id':inventory_item_id, 'available_qty':int(available_qty)})
                    else:
                        pass
            return graph_data,location_id
                    # else:
                    #     location_id = stock_location.search([],limit=1)
                    #     shopify_product = shopify_prod_obj.with_user(self.env.user).search([
                    #             ('product_variant_id', '=', product_id.id),
                    #             ('shopify_config_id', '=',
                    #              shopify_config_rec.id)], limit=1)
                    #     inventory_item_id = shopify_product.shopify_inventory_item_id
                    #     update_shopify_inv = shopify_product.update_shopify_inv
                    #     if inventory_item_id and update_shopify_inv:
                    #         return inventory_item_id,available_qty,location_id

