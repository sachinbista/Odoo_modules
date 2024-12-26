##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _, registry
from .. import shopify
from odoo.exceptions import AccessError, ValidationError
from datetime import time
import logging

_logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _inherit = 'stock.location'

    # shopify_legacy = fields.Boolean("Shopify Legacy", copy=False)
    # shopify_location_id = fields.Char(
    #     string="Shopify Location ID",
    #     copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)
    is_shopify_return_location = fields.Boolean('Is Shopify Return Location?',
                                                default=False,
                                                copy=False)
    is_shopify_location = fields.Boolean('Is Shopify Location?',
                                         default=False,
                                         copy=False)

    @api.model
    def _search(self, args, offset=0, limit=None, order=None,
                access_rights_uid=None):
        context = self._context or {}
        if context.get('from_shopify_refund_invoice') and context.get('shopify_config_id'):
            mapping_location_ids = self.env['shopify.location.mapping'].search(
                [('shopify_config_id', '=', context.get('shopify_config_id'))])

            if mapping_location_ids:
                args += [('id', 'in', mapping_location_ids.mapped('odoo_location_id.id'))]

        return super(StockLocation, self)._search(
            args, offset, limit, order, access_rights_uid=access_rights_uid)

    def shopify_import_location(self, shopify_config):
        """ Import locations under warehouse created for this instance.
        Create warehouse for each shopify instance. """
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Locations",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_location',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_config.check_connection()
            error_log_env = self_cr.env['shopify.error.log']
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            locations = shopify.Location.find()
            # warehouse = self_cr._get_warehouse(shopify_config)
            for location in locations:
                location_data = location.attributes
                job_descr = _("Create/Update Location:   %s") % (location_data.get('name'))

                log_line_vals.update({
                    'name': job_descr,
                    'id_shopify': f"Location: {location_data.get('id') or ''}",
                    'parent_id': parent_log_line_id.id
                })
                log_line_id = shopify_log_line_obj.create(log_line_vals)

                self_cr.with_company(shopify_config.default_company_id).with_delay(description=job_descr, max_retries=5).import_locations(location_data, shopify_config,
                                                                                       log_line_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            cr.commit()
            return True
        except Exception as e:
            cr.rollback()
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise Warning(_(e))
            # if hasattr(e, "response"):
            #     if e and e.response.code == 429 and e.response.msg == "Too Many Requests":
            #         time.sleep(5)
            #         self.shopify_import_location(shopify_config)
            # error_message = "Import Location have following error %s" % e
            # shopify_log_id = error_log_env.create_update_log(
            #     shopify_config_id=shopify_config,
            #     operation_type='import_location')
            # error_log_env.create_update_log(
            #     shop_error_log_id=shopify_log_id,
            #     shopify_log_line_dict={'error': [
            #         {'error_message': error_message}]})
            # _logger.error(_(error_message))

    def import_locations(self, location_data, shopify_config, log_line_id):
        try:
            shopify_location_mapping = self.env['shopify.location.mapping']
            shopify_location_mapping_id = shopify_location_mapping.search([
                ('shopify_location_id', '=', location_data.get('id')),
                ('shopify_config_id', '=', shopify_config.id)])
            if not shopify_location_mapping_id:
                # create a line in shppify_location_mapping table
                shopify_location_vals = {
                    'shopify_location_name': location_data.get('name'),
                    'shopify_config_id': shopify_config.id,
                    'shopify_location_id': location_data.get('id'),
                    'shopify_legacy': location_data.get('legacy')
                }
                shopify_location_mapp = self.env['shopify.location.mapping'].create(shopify_location_vals)
                # Check if default stock location does not have shopify location id, rename it as shopify location
                # if warehouse.lot_stock_id and not warehouse.lot_stock_id.shopify_location_id:
                #     warehouse.lot_stock_id.write(location_vals)
                # else:
                #     location_vals.update({
                #         'location_id': warehouse.view_location_id.id,
                #         'company_id': shopify_config.default_company_id.id
                #     })
                #     location_id = self.create(location_vals)
            else:
                # Update location name
                shopify_location_mapping_id.sudo().write({'shopify_location_name': location_data.get('name')})
            # TODO: Deactivate location
            # view_location = warehouse and warehouse.view_location_id
            # if view_location:
            #     locations = self.search(['|', ('location_id', '=', view_location.id),
            #                              ('id', '=', view_location.id)])
            #     locations.sudo().write({'active': location_data.get('active')})
            log_line_id.update({
                'state': 'success',
                'related_model_name': 'shopify.location.mapping',
                'related_model_id': shopify_location_mapping_id.id,
            })
        except Exception as e:
            log_line_id.update({
                'state': 'error',
                'message': 'Failed to import Location : {}'.format(e)
            })

    def _get_warehouse(self, shopify_config):

        warehouse_env = self.env['stock.warehouse']

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
                         'location_id': warehouse.view_location_id.id
                         })
        return warehouse


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)
