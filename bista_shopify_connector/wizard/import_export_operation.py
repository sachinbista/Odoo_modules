##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, ValidationError


_logger = logging.getLogger(__name__)


class ShopifyImportExportOperation(models.TransientModel):
    _name = 'shopify.import.export.operation'
    _description = 'Shopify Import Export Operation'
    _rec_name = 'shopify_config_id'

    def _get_default_from_date(self):
        shop_config = self._get_default_shopify_config()
        shopify_config = self.env['shopify.config'].browse(shop_config)
        key_name = 'shopify_config_%s' % (str(shopify_config.id))
        paramter_id = self.env['ir.config_parameter'].sudo().search([('key', '=', key_name)])
        value2 = paramter_id.value
        dict = eval(value2)
        last_import_order_date_str = dict.get('last_import_order_date')
        last_import_order_date = ''
        if last_import_order_date_str:
            last_import_order_date = datetime.strptime(last_import_order_date_str, '%Y/%m/%d %H:%M:%S')
            from_date = last_import_order_date or fields.Datetime.now() - timedelta(
                1)
            from_date = fields.Datetime.to_string(from_date)
            return from_date
        else:
            from_date = last_import_order_date or fields.Datetime.now() - timedelta(
                1)
            from_date = fields.Datetime.to_string(from_date)
            return from_date


    def _get_default_shopify_config(self):
        if 'shopify_config_id' in self.env.context:
            shopify_config_id = self.env.context.get('shopify_config_id', False)
        else:
            shopify_config_id = self.env['shopify.config'].search([('state', '=', 'success')], limit=1).id
        return shopify_config_id

    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade',
                                        default=_get_default_shopify_config)
    shopify_operation = fields.Selection(
        [("import", "Import"), ("export", "Export")
         ], default="import", string="Operation Type")
    import_operation = fields.Selection([
        ("import_customer", "Import Customers"),
        ("import_order", "Import Orders"),
        ("import_order_by_ids", "Import Orders(By Shopify IDs)"),
        ("import_product", "Import Products"),
        ("import_product_by_ids", "Import Products(By Shopify IDs)"),
        ("import_collection", "Import Collection"),
        ("import_location", "Import Location"),
        ("import_stock", "Import Stock"),
        ("import_refund", "Import Refund/Credit Note"),
        ("import_return", "Import Returns"),
        ("import_payouts","Import Payouts")
    ], string="Import")

    export_operation = fields.Selection([
        ("export_collection", "Export Collections"),
        ("export_product", "Export Products"),
        # ("export_refund", "Export Refund/Credit Note"),
        ("export_stock", "Export Stock"),
        ("update_collection", "Update Collections"),
        # ("update_location", "Update Locations"),
        ("update_product", "Update Products"),
        ("update_order_status", "Update Order Status"),
    ], string="Export")
    shopify_product_by_ids = fields.Char(string="Shopify Product Ids",
                                         help="E.g.'6774729736329','747297363329")
    shopify_order_by_ids = fields.Char(string="Shopify Order Ids",
                                       help="E.g.'6774729736329','747297363329")
    from_order_date = fields.Datetime("From Date", default=_get_default_from_date)
    to_order_date = fields.Datetime("To Date", default=fields.Datetime.now)
    is_run_and_active = fields.Boolean(string='Active Connection/Run Scheduled')
    is_order_by_date_range = fields.Boolean(string='Is Import order by date range?',
                                            help='This column enable option to import order by specific date range. '
                                                 'While this option is checked last import order date will not be updated.')

    @api.onchange('import_operation')
    def onchange_import_operation(self):
        if self.import_operation != 'import_order':
            self.is_order_by_date_range = False

    def shopify_run_operation(self):
        """
        This method used for fetch/export the operation based on selection
        operation in form.
        create queue for import customer, product and order.
        """
        if not self.shopify_config_id:
            raise UserError(_("Please select Shopify Configuration to process."))
        shopify_config = self.shopify_config_id
        if self.shopify_operation == 'import':

            if self.import_operation == "import_customer":
                self.env['res.partner'].with_delay(description="Import All Customer",
                                                   max_retries=5).shopify_import_customers(shopify_config)

            elif self.import_operation == 'import_product':
                self.env['shopify.product.template'].with_delay(description="Import All Products",
                                                                max_retries=5).shopify_import_product(shopify_config)

            elif self.import_operation == 'import_product_by_ids':
                self.env['shopify.product.template'].with_delay(
                    description=f'Import Product by ID: {self.shopify_product_by_ids}',
                    max_retries=5).shopify_import_product_by_ids_with_queue(shopify_config, self.shopify_product_by_ids)

            elif self.import_operation == 'import_collection':
                self.env['shopify.product.collection'].with_delay(description="Import All Collections",
                                                                  max_retries=5).shopify_import_product_collection(
                    shopify_config)

            elif self.import_operation == 'import_stock':
                self.env['shopify.product.template'].with_delay(description="Import Stock",
                                                                max_retries=5).shopify_import_stock(shopify_config)

            elif self.import_operation == 'import_order':
                self.env['sale.order'].with_delay(description="Import All Orders",
                                                  max_retries=5).shopify_import_orders(
                    shopify_config, self.from_order_date, self.to_order_date, self.is_order_by_date_range)

            elif self.import_operation == 'import_order_by_ids':
                self.env['sale.order'].with_delay(description=f'Import Order by ID: {self.shopify_order_by_ids}',
                                                  max_retries=5).shopify_import_order_by_ids(shopify_config,
                                                                                             self.shopify_order_by_ids)
            elif self.import_operation == 'import_location':
                self.env['stock.location'].with_delay(description="Import Locations",
                                                      max_retries=5).shopify_import_location(shopify_config)
            elif self.import_operation == 'import_refund':
                # self.env['account.move'].shopify_import_refunds(shopify_config)
                self.env['account.move'].with_delay(description="Import Refunds",
                                                    max_retries=5).shopify_import_refund_orders(shopify_config)
            elif self.import_operation == 'import_return':
                self.env['sale.order'].with_delay(description="Import Returns",
                                                  max_retries=5).shopify_import_return_orders(shopify_config)
            elif self.import_operation == 'import_payouts':
                self.env['shopify.payout'].with_delay(description="Import Payouts",
                                                      max_retries=5).shopify_import_payouts(shopify_config)
        elif self.shopify_operation == 'export':
            if self.export_operation == 'export_collection':
                self.env['shopify.product.collection'].with_delay(description="Export Collections",
                                                                  max_retries=5).shopify_export_product_collection(
                    shopify_config)
            elif self.export_operation == 'update_collection':
                self.env['shopify.product.collection'].with_delay(description="Update Collections",
                                                                  max_retries=5).shopify_update_product_collection(
                    shopify_config)
            elif self.export_operation == 'export_product':
                shopify_config.with_delay(description="Export Products",
                                          max_retries=5).export_products_to_shopify()
            elif self.export_operation == 'update_product':
                shopify_config.update_products_to_shopify()
            elif self.export_operation == 'export_stock':
                shopify_config.with_delay(description="Export Stock",
                                          max_retries=5).export_stock_to_shopify()
            elif self.export_operation == 'update_order_status':
                self.env['sale.order'].with_delay(description="Update Order Status",
                                                  max_retries=5).shopify_update_order_status(shopify_config)
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
