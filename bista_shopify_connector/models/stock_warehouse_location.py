##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _
from .. import shopify
from odoo.exceptions import AccessError, ValidationError
from datetime import time
import logging
_logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _inherit = 'stock.location'

    shopify_legacy = fields.Boolean("Shopify Legacy", copy=False)
    shopify_location_id = fields.Char(
        string="Shopify Location ID",
        copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)
    is_shopify_return_location = fields.Boolean()

    def shopify_import_location(self, shopify_config):
        """ Import locations under warehouse created for this instance.
        Create warehouse for each shopify instance. """
        shopify_config.check_connection()
        warehouse_env = self.env['stock.warehouse']
        error_log_env = self.env['shopify.error.log']
        try:
            locations = shopify.Location.find()
            # Search for warehouse for current instance
            warehouse = warehouse_env.search([
                    ('company_id', '=', shopify_config.default_company_id.id),
                    ('shopify_config_id', '=', shopify_config.id),
                    '|', ('active', '=', True), ('active', '=', False)])
            if not warehouse:
                # Note: There are chances that first/last 5 digits of store ID could be same, in that case we need to
                # use another unique column for warehouse code.
                warehouse_vals = {'name': shopify_config.name,
                                  'shopify_config_id': shopify_config.id,
                                  'code': shopify_config.shopify_shop_id[-5:]}
                warehouse = warehouse_env.create(warehouse_vals)
                view_location = warehouse.view_location_id
                if view_location:
                    view_location.sudo().write({
                        'shopify_config_id': shopify_config.id,
                    })
            return_location_id = self.search(
                [('company_id', '=', shopify_config.default_company_id.id),
                 ('name', '=', "Return: " + shopify_config.name),
                 ('location_id', '=', warehouse.view_location_id.id),
                 ('is_shopify_return_location', '=', True),
                 ('shopify_config_id', '=', shopify_config.id)])
            if not return_location_id:
                # Create a return location for each shopify warehouse
                self.create({'name': "Return: " + shopify_config.name,
                             'shopify_config_id': shopify_config.id,
                             'is_shopify_return_location': True,
                             'company_id': shopify_config.default_company_id.id,
                             'location_id':  warehouse.view_location_id.id
                             })
            for location in locations:
                location_data = location.attributes
                location_id = self.search([('shopify_location_id', '=', location_data.get('id')),
                                           ('shopify_config_id', '=', shopify_config.id)])
                if not location_id:
                    # Create new location if it does not exist
                    location_vals = {'name': location_data.get('name'),
                                     'shopify_config_id': shopify_config.id,
                                     'shopify_location_id': location_data.get('id'),
                                     'shopify_legacy': location_data.get('legacy')
                                     }
                    # Check if default stock location does not have shopify location id, rename it as shopify location
                    if warehouse.lot_stock_id and not warehouse.lot_stock_id.shopify_location_id:
                        warehouse.lot_stock_id.write(location_vals)
                    else:
                        location_vals.update({
                            'location_id': warehouse.view_location_id.id,
                            'company_id': shopify_config.default_company_id.id
                        })
                        location_id = self.create(location_vals)
                else:
                    # Update location name
                    location_id.sudo().write({'name': location_data.get('name')})
                # TODO: Deactivate location
                # view_location = warehouse and warehouse.view_location_id
                # if view_location:
                #     locations = self.search(['|', ('location_id', '=', view_location.id),
                #                              ('id', '=', view_location.id)])
                #     locations.sudo().write({'active': location_data.get('active')})
        except Exception as e:
            if hasattr(e, "response"):
                if e and e.response.code == 429 and e.response.msg == "Too Many Requests":
                    time.sleep(5)
                    self.shopify_import_location(shopify_config)
            error_message = "Import Location have following error %s" % e
            shopify_log_id = error_log_env.create_update_log(
                shopify_config_id=shopify_config,
                operation_type='import_location')
            error_log_env.create_update_log(
                shop_error_log_id=shopify_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': error_message}]})
            _logger.error(_(error_message))


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)
