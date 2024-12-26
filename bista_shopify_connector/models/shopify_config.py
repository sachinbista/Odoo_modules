##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from .. import shopify
import logging
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError,UserError
import dateutil
from pytz import timezone
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import json
import time
import requests
import pandas as pd
_shopify_allow_weights = ['kg', 'lb', 'oz', 'g']
_logger = logging.getLogger(__name__)


class ShopifyConfig(models.Model):
    _name = 'shopify.config'
    _description = 'Shopify Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'name'

    def sale_based_on_month(self,rec):
        query = """SELECT to_char(date_order,'Month') as mon,
                    SUM(amount_total) as monthly_sum FROM sale_order sale 
                    WHERE sale.shopify_config_id = %s GROUP BY mon ORDER BY mon ASC""" % rec
        return query

    def sale_based_on_week(self,rec):
        query = """SELECT DATE_PART('Week',date_order) as week,
                    SUM(amount_total) as weekly_sum FROM sale_order sale 
                    WHERE sale.shopify_config_id = %s GROUP BY week ORDER BY week ASC""" % rec
        return query

    def sale_based_on_year(self,rec):
        query = """SELECT DATE_PART('Year',date_order) as year,
                    SUM(amount_total) as yearly_sum FROM sale_order sale 
                    WHERE sale.shopify_config_id = %s GROUP BY year ORDER BY year ASC""" % rec
        return query

    def return_query(self,rec):
        if rec.month_data == True:
            query = self.sale_based_on_month(rec.id)
            return query
        elif rec.week_data == True:
            query = self.sale_based_on_week(rec.id)
            return query
        elif rec.year_data == True:
            query = self.sale_based_on_year(rec.id)
            return query

    @api.depends('week_data','month_data','year_data')
    def compute_kanban_data(self):
        datas = []
        for rec in self:
            query = self.return_query(rec)
            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            if query_results:
                for result in query_results:
                    if rec.month_data == True:
                        datas.append({"value": result.get('monthly_sum'), "label":result.get('mon')})
                    elif rec.week_data == True:
                        datas.append({"value": result.get('weekly_sum'), "label":'Week'+str(int(result.get('week')))})
                    elif rec.year_data == True:
                        datas.append({"value": result.get('yearly_sum'), "label":result.get('year')})
            else:
                datas = []
            rec.kanban_dashboard_graph = json.dumps([{'values': datas, 'id': rec.id}])

    def update_month(self):
        for rec in self:
            rec.week_data = False
            rec.year_data = False
            rec.month_data = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_week(self):
        for rec in self:
            rec.year_data = False
            rec.month_data = False
            rec.week_data = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def update_year(self):
        for rec in self:
            rec.month_data = False
            rec.week_data = False
            rec.year_data = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _get_shopify_operation_count(self):
        for shop in self:
            shop.shopify_customer_count = self.env[
                'res.partner'].search_count([('shopify_config_id', '=', shop.id),
                                             ('parent_id', '=', False),
                                             ('shopify_customer_id','!=',False)])  # only consider main partners.

            shop.shopify_product_count = self.env['product.template'].search_count([
                ('shopify_product_template_ids.shopify_config_id', '=', shop.id)])

            shop.shopify_order_count = self.env[
                'sale.order'].search_count([('shopify_config_id', '=', shop.id)
                ])
            shop.shopify_invoice_count = self.env[
                'account.move'].search_count([('move_type', '=', 'out_invoice'),
                                              ('shopify_config_id', '=', shop.id)
                ])
            shop.shopify_credit_note_count = self.env[
                'account.move'].search_count([('move_type', '=', 'out_refund'),
                                              ('shopify_config_id', '=', shop.id)
                ])
            shop.shopify_delivery_count = self.env[
                'stock.picking'].search_count([('picking_type_id.code', '=', 'outgoing'),
                                               ('shopify_config_id', '=', shop.id)
                ])

    kanban_dashboard_graph = fields.Text(compute="compute_kanban_data",help='This field computes the total sales data for kanban.')
    week_data = fields.Boolean('Week Data',default=True)
    month_data = fields.Boolean('Month Data',default=False)
    year_data = fields.Boolean('Year Data',default=False)
    name = fields.Char(string='Name',
                       help='Name of Connection',
                       tracking=True,
                       required=True)
    shop_url = fields.Char(string='Shop URL',
                           required=True,
                           help='Add Shopify shop url.',
                           tracking=True)
    api_key = fields.Char(string="Api Key",
                          help='Add an API key to shopify private applications.',
                          tracking=True,
                          required=True)
    password = fields.Char(string="Password",
                           help='Add the password of your shopify private application.',
                           required=True)
    default_company_id = fields.Many2one("res.company",
                                         string="Company",
                                         help='Select the company of shopify Application.',
                                         tracking=True,
                                         required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse',help='Default warehouse which will be added to Sales Orders.')

    state = fields.Selection([('draft', 'Draft'), ('success', 'Success'),
                              ('fail', 'Fail')],
                             string='Status',
                             help='Connection status of records',
                             default='draft')
    sync_product = fields.Selection([('sku', 'SKU'), ('barcode', 'Barcode'),
                                    ('sku_barcode', 'SKU or Barcode')],
                                    string='Sync Product with',
                                    help='Connector will sync products based on Barcode or SKU',
                                    default='sku',
                                    tracking=True)
    active = fields.Boolean(string='Active',
                            tracking=True,
                            default="True",
                            help='Active/Inactive shopify config.')
    is_create_product = fields.Boolean(string='Create Odoo Products?',
                                       tracking=True, default="True",
                                       help="If true will create a new product in odoo.")
    is_sync_product_image = fields.Boolean(string='Sync Product Images?',
                                           tracking=True, default="True",help='Import product images while importing products from Shopify.')
    # Commented to avoid recurring live sync from odoo to shopify when set to False.
    # When this boolean is False, User will have to manually click on 'Apply' button in stock quants and
    # this will update stock on shopify through live sync feature
    # is_validate_inv_adj = fields.Boolean(string='Validate Inventory Adjustment?',
    #                                      tracking=True,
    #                                      help='Whether to auto-validate inventory adjustment created during import stock operation.')
    is_pay_unearned_revenue = fields.Boolean(string='Do you want to go with unearned revenue payment flow?',
                                             tracking=True,help='Whether to add payment in Odoo as down-payment or normal payment.')
    is_use_shop_seq = fields.Boolean(string='Use Shopify Order Sequence?',
                                     tracking=True,help='If checked, Order will be created with Shopify order number else with Odoo default sequence.')
    shopify_order_prefix = fields.Char(string="Order Prefix",
                                       help="Enter Shopify order prefix",
                                       tracking=True)
    is_auto_archive = fields.Boolean(string='Auto Archive order in Shopify once '
                                            'shipped in Odoo?',
                                     tracking=True)
    is_risk_order = fields.Boolean(string='Fetch Risk Order Details?',
                                   tracking=True)
    is_refund_auto_paid = fields.Boolean(string='Auto paid refund in Odoo?',
                                         tracking=True)
    is_auto_invoice_paid = fields.Boolean(
        string='Auto create/paid invoice for manually processes delivery order in Odoo?',
        help="If checked, auto create invoice and reconciled payment.",
        tracking=True)
    shopify_customer_count = fields.Integer(string='Customer Count',
                                            compute='_get_shopify_operation_count')
    shopify_product_count = fields.Integer(string='Product Count',
                                           compute='_get_shopify_operation_count')
    shopify_order_count = fields.Integer(string='Order Count',
                                         compute='_get_shopify_operation_count')
    shopify_invoice_count = fields.Integer(string='Invoice Count',
                                           compute='_get_shopify_operation_count')
    shopify_credit_note_count = fields.Integer(string='Credit Note Count',
                                           compute='_get_shopify_operation_count')
    shopify_delivery_count = fields.Integer(string='Delivery Count',
                                            compute='_get_shopify_operation_count')
    timezone = fields.Char("Shop Timezone", help="Shopify configured timezone")
    timezone_name = fields.Char("Shop Timezone Name", help="Shopify "
                                                           "configured "
                                                           "timezone name.")
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist',help='Pricelist to be set on sales order.')
    shipping_product_id = fields.Many2one('product.product', 'Shipping Product',help='Product used for Shopify Shipping charges.')
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Account',help='Analytic Account which will be added on Sales orders and Invoices imported through this configuration.')
    sale_team_id = fields.Many2one('crm.team', 'Sales Team',
        help='Sales team which will be selected on sales orders by default.')
    default_tax_account_id = fields.Many2one('account.account',
                                             'Tax Account',help="Tax account to be selected on Taxes(Repartition for Invoices) while creating new tax on import order operation.")
    default_tax_cn_account_id = fields.Many2one('account.account',
                                                'Tax Account on Credit Notes',help='Tax account to be selected on Taxes(Repartition for Credit Notes) while creating new tax on import order operation.')
    default_rec_account_id = fields.Many2one('account.account',
                                             'Receivable Account',help='Receivable account will be assigned to customers while importing customers.')
    default_pay_account_id = fields.Many2one('account.account', 'Payable Account',help='Payable account will be assigned to customer s while importing customers.')
    unearned_account_id = fields.Many2one('account.account',
                                          'Unearned Revenue Account',help='Account which will be used on invoice when there is advance payment.')
    rounding_diff_account_id = fields.Many2one('account.account',
                                               'Rounding Difference Account',
                                               help='Account which will be used for rounding difference of imported orders')

    default_customer_id = fields.Many2one('res.partner', 'Customer',help='Set a default customer which will be used when there is no customer on shopify orders.')
    default_payment_term_id = fields.Many2one('account.payment.term', 'Payment Term',help='Default payment term to be added on sales order while importing sales order.')
    shopify_shop_id = fields.Char("Shop ID")
    shopify_shop_name = fields.Char("Shop Name", help="Shopify Shop Name")
    shopify_shop_currency = fields.Char(string="Shop Currency",
                                        help="Shopify Configured Currency")
    shopify_shop_owner = fields.Char("Shop Owner", help="Shopify Owner Name")
    workflow_line_ids = fields.One2many("shopify.workflow.line",
                                        "shopify_config_id",
                                        string="Shopify Workflow Lines")
    color = fields.Integer(string='Color Index')
    last_import_order_date = fields.Datetime(string='Last Order Import Date')
    last_import_customer_date = fields.Datetime('Last Import Customer Date')
    last_product_import_date = fields.Datetime('Last Import Products Date')
    last_stock_import_date = fields.Datetime('Last Import Stock Date')
    webhook_ids = fields.One2many("shopify.webhook", "shopify_config_id", "Webhooks",context={'active_test': False})
    last_stock_export_date = fields.Datetime('Last Export Stock Date')
    last_refund_import_date = fields.Datetime('Last Import Refunds Date')
    last_return_order_import_date = fields.Datetime('Last Import Return Date')
    financial_workflow_ids = fields.One2many('shopify.financial.workflow', 'shopify_config_id', string='Financial Workflow')
    # payout_ids = fields.One2many("shopify.payout.config", "shopify_config_id",
    #                                        string="Payouts")
    last_payout_import_date = fields.Datetime('Last Payout Import Date')
    shopify_tag_ids = fields.Many2many('shopify.tags',string='Shopify Tags')
    shopify_product_id = fields.Many2one('product.product', 'Shopify Product',help='Product used if any odoo product is not found while sync.')
    is_create_customer = fields.Boolean(string='Create Customers?',
                                       tracking=True, default="True",
                                       help='If true will set a default customer which will be used when there is no customer on shopify orders.')
    shopify_payout_journal_id = fields.Many2one('account.journal',
                                                string='Payout Report Journal')
    is_sync = fields.Boolean(string='Is Sync', tracking=True)
    shopify_location_id = fields.Char('Shopify Location')


    def import_export_data(self):
        """Import/Export data from/to Shopify."""
        context = self._context
        # check connection state
        for t_con in self.search([('state', '!=', 'success'),('active','=',True)]):
            t_con.check_connection()
        for config in self.search([('state', '=', 'success'),('active','=',True)]):
            if context.get('from_cust'):
                self.env['res.partner'].shopify_import_customers(config)
            elif context.get('from_order'):
                self.env['sale.order'].shopify_import_orders(config)
            elif context.get('from_location'):
                self.env['stock.location'].shopify_import_location(config)
            elif context.get('from_collection'):
                self.env['shopify.product.collection'].shopify_import_product_collection(config)
            elif context.get('export_collection'):
                self.env['shopify.product.collection'].shopify_export_product_collection(config)
            elif context.get('export_product'):
                config.export_products_to_shopify()
            elif context.get('export_stock'):
                config.export_stock_to_shopify()
            elif context.get('import_product'):
                self.env['shopify.product.template'].shopify_import_product(config)
            elif context.get('from_refund'):
                self.env['account.move'].shopify_import_refund_orders(config)
            elif context.get('from_order_status'):
                self.env['sale.order'].shopify_update_order_status(config)
            elif context.get('from_stock'):
                self.env['shopify.product.template'].shopify_import_stock(config)
            elif context.get('from_process_queue'):
                queue_job = self.env['shopify.queue.job']
                for queue in queue_job.search([('state', '=', 'draft')],limit=1):
                    queue.queue_process()

    def action_create_queue(self, operation_type):
        self.ensure_one()
        queue_obj = self.env['shopify.queue.job']
        return queue_obj.create({'operation_type': operation_type,
                                 'shopify_config_id': self.id})

    def shopify_archive_active(self):
        """This method will set the shopify config to archive/active"""
        if self.active:
            self.update({"active": False})
            self.reset_to_draft()
        else:
            self.update({"active": True})

    def action_open_shopify_configuration_view(self):
        """ This method will show shopify configuration actions"""
        self.ensure_one()
        return {
            'name': _('Shopify Configuration'),
            'res_model': 'shopify.config',
            'context': self._context,
            'view_mode': 'form',
            'res_id': self.id,
            'view_id': self.env.ref('bista_shopify_connector.view_shopify_config_form').id,
            'type': 'ir.actions.act_window',
        }

    def action_shopify_sale_report(self):
        """ This method will redirect to shopify sale report"""
        self.ensure_one()
        module_sale_enterprise = self.env['ir.module.module'].search([
                ('name','=','website_sale'),
                ('state','=','installed')],limit=1)
        if not module_sale_enterprise:
            action = self.env.ref('bista_shopify_connector.shopify_sale_order_action').read()[0]
            action['domain'] = [('shopify_config_id', '=', self.id)]
        else:
            action = self.env.ref('website_sale.sale_report_action_dashboard').read()[0]
            action['domain'] = [('order_id.shopify_config_id', '=', self.id)]
        return action

    def action_shopify_queue_operations(self):
        """ This method will redirect to shopify queue operations"""
        self.ensure_one()
        action = self.env.ref('bista_shopify_connector.action_shop_queue_job').read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_log_operations(self):
        """ This method will redirect to shopify log operations"""
        self.ensure_one()
        action = self.env.ref('bista_shopify_connector.action_shopify_error_log').read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def action_wizard_shopify_import_export_operations(self):
        """ This method will show shopify operation actions"""
        self.ensure_one()
        action = self.env.ref(
            'bista_shopify_connector.action_wizard_shopify_import_export_operations').read()[0]
        action['context'] = {'default_shopify_config_id': self.id}
        return action

    def action_shopify_customer(self):
        """ This method will show shopify customer actions"""
        self.ensure_one()
        action = self.env.ref('base.action_partner_form').read()[0]
        action['domain'] = [('parent_id', '=', False),
                            ('shopify_config_id', '=', self.id),
                            ('shopify_customer_id', '!=', False)]
        return action

    def action_shopify_product(self):
        """ This method will show shopify product actions"""
        self.ensure_one()
        action = self.env.ref('product.product_template_action_all').read()[0]
        action['domain'] = [('shopify_product_template_ids.shopify_config_id', '=', self.id)]
        return action

    def action_shopify_order(self):
        """ This method will show shopify orders actions"""
        self.ensure_one()
        action = self.env.ref('sale.action_orders').read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_invoice(self):
        """ This method will show shopify invoice actions"""
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [('move_type', '=', 'out_invoice'), ('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_credit_note(self):
        """ This method will show shopify credit note actions"""
        self.ensure_one()
        action = self.env.ref('account.action_move_out_refund_type').read()[0]
        action['domain'] = [('move_type', '=', 'out_refund'),
                            ('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_delivery(self):
        """ This method will show shopify delivery actions"""
        self.ensure_one()
        action = self.env.ref("stock.action_picking_tree_all").read()[0]
        action['domain'] = [('picking_type_id.code', '=', 'outgoing'), ('shopify_config_id', '=', self.id)]
        return action

    def action_active_locations(self):
        """ This method will show shopify delivery actions"""
        self.ensure_one()
        action = self.env.ref("stock.action_location_form").read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def schedulers_configuration_action(self):
        """ This method will show shopify scheduler actions"""
        self.ensure_one()
        action = self.env.ref('base.ir_cron_act').read()[0]
        action['domain'] = ['|', ('name', 'ilike', self.name),
                            ('name', 'ilike', 'shopify')]
        return action

    def action_active_schedulers(self):
        """ This method will show shopify avtive scheduler actions"""
        self.ensure_one()
        action = self.env.ref('base.ir_cron_act').read()[0]
        action['domain'] = ['|', ('name', 'ilike', self.name),
                            ('name', 'ilike', 'shopify'), ('active', '=', True)]
        return action

    def reset_to_draft(self):
        """ This method will set the shopify config to draft state """
        self.update({'state': 'draft'})

    def convert_shopify_datetime_to_utc(self, date):
        converted_datetime = ""
        if date:
            shop_date = dateutil.parser.parse(date)
            converted_datetime = shop_date.astimezone(timezone('UTC')).strftime(
                '%Y-%m-%d %H:%M:%S')
        return converted_datetime or False

    def check_connection(self):
        """
        This function check that shopify store is exist or not using api_key,
        password and shop_url
        """
        for rec in self:
            try:
                api_key = rec.api_key or ''
                password = rec.password or ''
                shop_url = rec.shop_url and "%s/admin" % rec.shop_url or ''
                if api_key and password and shop_url:
                    shopify.ShopifyResource.set_user(api_key)
                    shopify.ShopifyResource.set_password(password)
                    shopify.ShopifyResource.set_site(shop_url)
                    shop = shopify.Shop.current()
                    if shop:
                        self.shopify_shop_id = shop.id
                        self.shopify_shop_name = shop.name
                        self.shopify_shop_currency = shop.currency
                        self.shopify_shop_owner = shop.shop_owner
                        self.timezone = shop.timezone
                        self.timezone_name = shop.iana_timezone
                        rec.update({'state': 'success'})
                    else:
                        rec.update({'state': 'fail'})
                else:
                    rec.update({'state': 'fail'})
                    self._cr.commit()
                    _logger.error('Invalid API key or access token: %s', e)
                    # raise Warning(
                    #     _('UnauthorizedAccess: Invalid API key or access token.'))
            except Exception as e:
                rec.update({'state': 'fail'})
                self._cr.commit()
                _logger.error('Invalid API key or access token: %s', e)
                # raise Warning(
                #     _('UnauthorizedAccess: Invalid API key or access token.'))


    def export_stock_to_shopify(self):
        """
        Export stock odoo to shopify
        """
        error_log_env = self.env['shopify.error.log']
        shopify_log_id = error_log_env.create_update_log(
            shopify_config_id=self,
            operation_type='export_stock')
        shopify_log_line_dict = {'error': [], 'success': []}
        self.check_connection()
        location_ids = self.env['stock.location'].search(
            [('shopify_config_id', '=', self.id), ('usage', '=', 'view'),
             ('shopify_location_id', '!=', False)])
        if not location_ids:
            log_message = "location not found for shopify config %s " % self.name
            shopify_log_line_dict['error'].append(
                {'error_message': 'Export STOCK: %s' % log_message})
            return False
        shopify_product_variants = self.env['shopify.product.product'].sudo().search(
            [('shopify_config_id', '=', self.id),
             ('update_shopify_inv', '=', True)])
        shopify_inventory_rec = self.env['shopify.inventory.queue']
        shopify_inventory_line = self.env['shopify.update.inventory.line']
        line_count = 0
        # for location_id in location_ids:
        #     if not location_ids:
        #         log_message = "Location not found for shopify config %s " % self.name
        #         shopify_log_line_dict['error'].append(
        #             {'error_message': 'Export stock: %s' % log_message})
        #         return False
        for shopify_variant_id in shopify_product_variants:
            product_variant_id = shopify_variant_id.product_variant_id
            if product_variant_id.detailed_type == 'product' and not shopify_variant_id.shopify_inventory_item_id:
                log_message = "Inventory item ID not found for Product Variant %s in export stock." % product_variant_id.name
                shopify_log_line_dict['error'].append(
                    {'error_message': 'Export stock: %s' % log_message})
                continue
            # qty_available = product_variant_id.with_context(
            #     {'location': location_id.id})._product_available()
            qty_available = product_variant_id.with_context(
                {'location': location_ids.ids})._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'))
            variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
            shopify_location_id = self.shopify_location_id
            shopify_inventory_item_id = shopify_variant_id.shopify_inventory_item_id
            if line_count < 1:
                shopify_inv = shopify_inventory_rec.create({'shopify_config_id': self.id,
                                                            'state': 'draft',
                                                            'operation_type': 'update_stock'})
            shopify_inv = shopify_inv
            if shopify_inv:
                shopify_inventory_line.create(
                    {'shop_queue_inventory_id': shopify_inv.id,
                     'shopify_location_id': shopify_location_id,
                     'shopify_inventory_item_id': shopify_inventory_item_id,
                     'variant_qty': int(variant_qty),
                     'name': shopify_variant_id.display_name})
                line_count += 1
                if line_count >= 100:
                    line_count = 0

                # try:
                #     shopify.InventoryLevel.set(shopify_location_id,
                #                                shopify_inventory_item_id,
                #                                int(variant_qty))
                #     _logger.info(
                #         'Export stock successfully for location "%s" inventory item id "%s" : %s' % (
                #         shopify_location_id, shopify_inventory_item_id, variant_qty))
                #
                # except Exception as e:
                #     if e.code == 429:
                #         time.sleep(5)
                #         shopify.InventoryLevel.set(shopify_location_id,
                #                                    shopify_inventory_item_id,
                #                                    int(variant_qty))
                #     else:
                #         log_message = "Facing a problem while exporting Stock for shopify product variant %s: %s" % (
                #         shopify_variant_id.display_name, str(e))
                #         shopify_log_line_dict['error'].append({'error_message': 'Export stock: %s' % log_message})
                #         continue
            self.last_stock_export_date = fields.Datetime.now()
            error_log_env.create_update_log(shopify_config_id=self,
                                            shop_error_log_id=shopify_log_id,
                                            shopify_log_line_dict=shopify_log_line_dict)
            # if not shopify_log_id.shop_error_log_line_ids:
            #     shopify_log_id.unlink()
        return True
    def update_shopify_inventory(self, shopify_location_id, inventory_item_id,
                                 qty, shopify_log_id):
        """
        Adjust qty on shopify base on given location_id and inventory_item_id
        """
        self.ensure_one()
        error_log_env = self.env['shopify.error.log']
        try:
            shopify.InventoryLevel.set(shopify_location_id,
                                          inventory_item_id, qty)
            _logger.info('Export stock successfully for location "%s" inventory item id "%s" : %s' % (shopify_location_id, inventory_item_id, qty))
        except Exception as e:
            error_log_env.create_update_log(
                shop_error_log_id=shopify_log_id,
                shopify_log_line_dict={
                    'error': [{'error_message': e}]})

    def export_products_to_shopify(self):
        """
        Fetch a product template ids which need to be updated on shopify
        and pass it to the export_product
        """
        self.ensure_one()
        user_id = self.env.user.id
        product_tmpl_ids = self.env['shopify.product.template'].with_user(
            user_id).search(
            [('shopify_config_id', '=', self.id),
             ('shopify_prod_tmpl_id', 'in', ['', False])])

        for prod_tmpl in product_tmpl_ids:
            self.export_product(prod_tmpl)

    def prepare_vals_for_export_product_details(self, products):
        """
        this method will use prepare shopify export product data
        :param products: shopify products
        :return: export shopify values
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        prod_weight_unit = get_param('product.weight_in_lbs')
        if prod_weight_unit == '1':
            weight_unit = self.env.ref('uom.product_uom_lb')
        else:
            weight_unit = self.env.ref('uom.product_uom_kgm')
        variants = []
        for s_product in products:
            variant_val = {}
            product = s_product.product_variant_id
            price = self.pricelist_id._get_product_price(product, 1.0,
                partner=False,
                    uom_id=product.uom_id.id)
            if product.default_code:
                default_code = product.default_code

                count = 1
                for value in product.product_template_attribute_value_ids:
                    variant_val.update(
                        {'option' + str(count): value.name})
                    count += 1

                if weight_unit and weight_unit.name in _shopify_allow_weights:
                    variant_val.update(
                        {'weight': product.weight,
                         'weight_unit': weight_unit.name})

                variant_val.update(
                    {
                        'price': s_product.lst_price > 0.0 and s_product.lst_price or float(price),
                        'sku': default_code or "",
                        "barcode": product.barcode or "",
                        'inventory_management': 'shopify',
                    })
                variants += [variant_val]
        return variants

    def export_product(self, s_product_tmpl_ids, shopify_locations_records=False):
        """
        Process Product template and pass it to the shopify

        1. Fetch Locations base on the shopify configuration
        2. Get Product template recordset from shopify_product_template masters
        3. Get Shopify product variants recordset using
            shopify_product_template masters
        4. Get attribute data from product template recordset
        5. Prepare product's variant vals using shopify_product_product
            recordset
            5.1 Variant's SKU, as well as weight and weight unit, are fetching
            from product variant
            5.2 sale price is fetched from shopify_product_product master
        6. Prepare vals for images using product template image and image_ids
            records
        7. Get tags data from using product template recordset (prod_tags_ids
            & province_tags_ids)
        8. Create Product Template on Shopify using the above details
        9. If a product is created successfully, then update
            shopify_template_id in shopify_product_template master and marked
            shopify_publsihed True in shopify_product_template master (to
            identify the product is created published on Shopify in future we
            can use this field to make product publish and unpublish on
            Shopify) else update an error message in the shopify_error_log
            field.
        10. Now update variants details in Odoo system as well as variant
            inventory and icon images on Shopify
            10.1 Get shopify variant vals using shopify create recordset
            10.2 Update an image on shopify for the variant
            10.3 Update shopify_product_id, shopify_inventory_item_id and
            shopify_product_template_id in shopify_product_product master
            10.4 Update an inventory for product for all locations
        """
        error_log_env = self.env['shopify.error.log']
        shopify_log_id = error_log_env.create_update_log(
            shopify_config_id=self,
            operation_type='export_product')
        self.ensure_one()
        shopify_config_id = self
        shopify_config_id.check_connection()
        shopify_prod_obj = self.env['shopify.product.product']
        error_log_obj = self.env['shopify.error.log']
        stock_quant_obj = self.env['stock.quant']
        location_obj = self.env['stock.location']
        # Fetch Locations based on the shopify configuration
        if not shopify_locations_records:
            shopify_locations_records = location_obj.with_user(self.env.user).search(
                [('shopify_config_id', '=', shopify_config_id.id),
                 ('shopify_location_id', '!=', False),
                 ('usage', '=', 'internal'),
                 ('shopify_legacy', '=', False)])

        # Get Product template recordset from shopify_product_template masters
        for s_product_tmpl_id in s_product_tmpl_ids:
            try:
                variants, options = [], []
                product_tmpl_id = s_product_tmpl_id.product_tmpl_id
                if product_tmpl_id.sale_ok:
                    # TO DO: Create a one2many relation shopify_product_template
                    # with shopify_product_product
                    # Get Shopify product variants recordset using
                    # shopify_product_template masters
                    products = shopify_prod_obj.with_user(self.env.user).\
                        search([('shopify_config_id', '=', shopify_config_id.id),
                                ('shopify_product_id', 'in', ['', False]),
                                ('product_variant_id', 'in',
                                 product_tmpl_id.product_variant_ids.ids)])
                    if products.ids:
                        # Get attribute data from product template recordset
                        for attribute_line in product_tmpl_id.attribute_line_ids:
                            options_val = {}
                            options_val.update(
                                {'name': attribute_line.attribute_id.name})
                            values = []
                            values = attribute_line.value_ids.mapped('name')
                            options_val.update({'values': values})
                            options += [options_val]

                        variants = self.prepare_vals_for_export_product_details(
                            products)
                    else:
                        error_msg = "Please set atleast one product variant for shopify product (%s) export" \
                                        % product_tmpl_id.name
                        error_log_obj.create_update_log(
                            shop_error_log_id=shopify_log_id,
                            shopify_log_line_dict={
                                'error': [
                                    {'error_message': error_msg}]})
                        continue
                else:
                    error_msg = "A product %s should be 'Can be Sold' before " \
                                "exporting" % (str(
                                product_tmpl_id.name))
                    error_log_obj.create_update_log(
                        shop_error_log_id=shopify_log_id,
                        shopify_log_line_dict={
                            'error': [
                                {'error_message': error_msg}]})
                    continue

                # Prepare vals for images using product template image
                # and product_multi_images records
                images = []
                if product_tmpl_id.image_1920:
                    images += [{'attachment': product_tmpl_id.image_1920.decode("utf-8"),
                                'position': 1}]
                for product_image in product_tmpl_id.product_multi_images:
                    if product_image.image:
                        images += [
                            {'attachment': product_image.image.decode("utf-8")}]

                # Get tags data from using product template recordset
                # (prod_tags_ids & province_tags_ids)
                prod_tags = product_tmpl_id.prod_tags_ids
                province_tags = product_tmpl_id.province_tags_ids
                str_prod_province_tags = []
                for prod_tag in prod_tags:
                    str_prod_province_tags.append(prod_tag.name)
                for prov_tag in province_tags:
                    str_prod_province_tags.append(prov_tag.name)
                tags = ",".join(str_prod_province_tags)
                # Create Product Template on Shopify using the above details
                new_product = shopify.Product()
                new_product.title = product_tmpl_id.name
                # new_product.published = s_product_tmpl_id.shopify_published
                new_product.published_scope = s_product_tmpl_id.shopify_published_scope
                if s_product_tmpl_id.product_type:
                    new_product.product_type = s_product_tmpl_id.product_type.name
                if s_product_tmpl_id.vendor:
                    new_product.vendor = s_product_tmpl_id.vendor.name
                if tags:
                    new_product.tags = tags
                if s_product_tmpl_id.body_html:
                    new_product.body_html = str(s_product_tmpl_id.body_html)
                else:
                    new_product.body_html = ''
                if options:
                    new_product.options = options
                if variants:
                    new_product.variants = variants
                if images:
                    new_product.images = images
                success = new_product.save()  # returns false if the record is invalid
                # If a product is created successfully, then update
                # shopify_template_id in shopify_product_template master and
                # marked shopify_publsihed True in shopify_product_template
                # master (to identify the product is created published on
                # Shopify in future we can use this field to make product
                # publish and unpublish on Shopify) else update an error
                # message in the shopify_error_log field.
                if success:
                    variant_updated = False
                    try:
                        shopify_product_tmpl_id = new_product.id
                        if shopify_product_tmpl_id:
                            for collection in s_product_tmpl_id.shopify_prod_collection_ids:
                                collects = []
                                collects.append({'product_id': new_product.id})
                                scollection = shopify.CustomCollection().find(
                                    collection.shopify_id)
                                if scollection:
                                    scollection.collects = collects
                                    scollection.save()
                            s_product_tmpl_id.update(
                                {'shopify_prod_tmpl_id': shopify_product_tmpl_id,
                                 'shopify_published': True,
                                 'shopify_handle': new_product.handle,
                                 'last_updated_date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                            # Get shopify variant vals using shopify create
                            # recordset
                            for variant in new_product.variants:
                                variant_id = variant.id

                                inventory_item_id = variant.inventory_item_id
                                default_code = variant.sku
                                shopify_product_product = shopify_prod_obj.with_user(self.env.user).\
                                    search([('shopify_config_id', '=', shopify_config_id.id),
                                            ('shopify_product_id',
                                             'in', ['', False]),
                                            ('product_template_id',
                                             '=', product_tmpl_id.id),
                                            ('default_code', '=', default_code)], limit=1)
                                product_variant_rec = shopify_product_product.product_variant_id

                                # Update an image on shopify for the variant
                                if product_variant_rec:
                                    variant_image = product_variant_rec.image_1920
                                    if variant_image:
                                        image = shopify.Image()
                                        image.product_id = shopify_product_tmpl_id
                                        image.attachment = variant_image.decode(
                                            "utf-8")
                                        image.save()
                                        variant.image_id = image.id
                                        try:
                                            variant.save()
                                        except Exception as e:
                                            _logger.error(
                                            _('Facing a problems while variant save on'
                                              ' image in exporting product!: %s') % e)
                                if shopify_product_product:
                                    # Update shopify_product_id,
                                    # shopify_inventory_item_id and
                                    # shopify_product_template_id in
                                    # shopify_product_product master
                                    shopify_product_product.with_user(self.env.user).update({'shopify_product_id': variant_id,
                                                                                             'shopify_product_template_id': s_product_tmpl_id.id,
                                                                                             'shopify_inventory_item_id': inventory_item_id,
                                                                                             'last_updated_date': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                                    variant_updated = True
                                    # Update an inventory for product for all
                                    # locations
                                    for shopify_locations_record in shopify_locations_records:
                                        shopify_location = shopify_locations_record.shopify_location_id
                                        shopify_location_id = shopify_locations_record.id
                                        available_qty = 0
                                        quants = stock_quant_obj.with_user(self.env.user).search(
                                            [('location_id.usage', '=', 'internal'),
                                             ('product_id', '=',
                                              shopify_product_product.product_variant_id.id),
                                             ('location_id', '=', shopify_location_id)])
                                        for quant in quants:
                                            available_qty += quant.quantity
                                        if available_qty and shopify_product_product.update_shopify_inv:
                                            location = shopify.InventoryLevel.set(
                                                shopify_location, inventory_item_id, int(available_qty))
                    except Exception as e:
                        new_product.destroy()
                        s_product_tmpl_id.update(
                            {'shopify_prod_tmpl_id': False,
                             'shopify_published': False,
                             'shopify_handle': False,
                             'last_updated_date': False})
                        if variant_updated:
                            shopify_products = shopify_prod_obj.sudo().search(
                                [('shopify_config_id', '=', shopify_config_id.id),
                                 ('shopify_product_id', '!=', False),
                                 ('product_template_id',
                                  '=', product_tmpl_id.id)], limit=1)
                            if shopify_products:
                                shopify_products.update({
                                    'shopify_product_id': False,
                                    'shopify_product_template_id': False,
                                    'shopify_inventory_item_id': False,
                                    'last_updated_date': False})
                        error_msg = 'Facing a problems while exporting product!' % e
                        error_log_obj.create_update_log(
                            shop_error_log_id=shopify_log_id,
                            shopify_log_line_dict={
                                'error': [
                                    {'error_message': error_msg}]})
            except Exception as e:
                _logger.error(
                    _('Facing a problems while exporting product!: %s') % e)
                error_msg = 'Facing a problems while exporting product!: %s' % e
                error_log_obj.create_update_log(
                    shop_error_log_id=shopify_log_id,
                    shopify_log_line_dict={
                        'error': [
                            {'error_message': error_msg}]})
                s_product_tmpl_id.shopify_error_log = str(e)

    def export_prod_variant(self, shopify_prod_rec):
        """
        Process to export product variant from odoo to shopify

        1. Check if product variant already exported or variant has shopify product template.
        2. Set the shopify product variant object and set variant attributes, weight unit, price,
           sku, inventory management, product_id.
        3. If product variant created successfully, then set images and metafields on product variant on
           shopify side. Also update the shopify product variant ID, inventory item ID and Product Template
           ID on shopify product variant one2many.
        4. Update the Inventory of the product variant on respective locations which are mapped with
           shopify locations.
        5. If any issue occurs during the variant export process, then raise the user warnings accordingly.
        """
        s_prod_tmpl = self.env['shopify.product.template']
        stock_quant_obj = self.env['stock.quant']
        error_log_obj = self.env['shopify.error.log']
        get_param = self.env['ir.config_parameter'].sudo().get_param
        prod_weight_unit = get_param('product.weight_in_lbs')

        if prod_weight_unit == '1':
            weight_unit = self.env.ref('uom.product_uom_lb')
        else:
            weight_unit = self.env.ref('uom.product_uom_kgm')
        for rec in self:
            rec.check_connection()
            shopify_log_id = error_log_obj.create_update_log(
                shopify_config_id=self,
                operation_type='export_product')
            config_id = rec.id
            if shopify_prod_rec.shopify_product_id:
                name = shopify_prod_rec.product_variant_id.name
                error_msg = "Variant %s is already exported to Shopify." % (
                    name)
                error_log_obj.create_update_log(
                    shop_error_log_id=shopify_log_id,
                    shopify_log_line_dict={
                        'error': [{'error_message': error_msg}]})
                continue
            product = shopify_prod_rec.product_variant_id
            product_tmpl_id = product.product_tmpl_id
            if product_tmpl_id.sale_ok:
                s_prod_tmpl_rec = s_prod_tmpl.sudo().search(
                    [('product_tmpl_id', '=', product_tmpl_id.id),
                     ('shopify_config_id', '=', config_id)], limit=1)
                if not s_prod_tmpl_rec:
                    error_msg = "'Shopify Product template %s record is not " \
                                "found. Kindly export a product template'" % (
                                    product_tmpl_id.name)
                    error_log_obj.create_update_log(
                        shop_error_log_id=shopify_log_id,
                        shopify_log_line_dict={'error': [{'error_message': error_msg}]})
                    continue
                else:
                    shopify_prod_tmpl_id = s_prod_tmpl_rec.shopify_prod_tmpl_id
                    if shopify_prod_tmpl_id:
                        shopify_prod = shopify.Variant()
                        count = 1
                        for value in product.product_template_attribute_value_ids:
                            # shopify_prod.'option' + str(count) = value.name
                            opt_cmd = 'shopify_prod.option' + str(
                                count) + " = '" + str(value.name) + "'"
                            exec(opt_cmd)
                            count += 1

                        if weight_unit and weight_unit.name in _shopify_allow_weights:
                            shopify_prod.weight = product.weight
                            shopify_prod.weight_unit = weight_unit.name
                        else:
                            _logger.error(
                                _('UOM is not define for product variant id!: %s') % str(
                                    product.id))

                        shopify_prod.price = shopify_prod_rec.lst_price
                        if product.default_code:
                            shopify_prod.sku = product.default_code
                        else:
                            error_msg = "Please set Internal reference for " \
                                        "product variant %s before exporting to shopify !" % (
                                            product.name)
                            error_log_obj.create_update_log(
                                shop_error_log_id=shopify_log_id,
                                shopify_log_line_dict={
                                    'error': [{'error_message': error_msg}]})
                            continue
                        shopify_prod.inventory_management = "shopify"
                        shopify_prod.product_id = shopify_prod_tmpl_id
                        success = shopify_prod.save()
                        if success:
                            variant_id = shopify_prod.id
                            inventory_item_id = shopify_prod.inventory_item_id
                            product_variant_rec = shopify_prod_rec.product_variant_id
                            # Update images on shopify variant
                            if product_variant_rec:
                                variant_image = product_variant_rec.image_1920
                                if variant_image:
                                    image = shopify.Image()
                                    image.product_id = shopify_prod_tmpl_id
                                    image.attachment = variant_image.decode(
                                        "utf-8")
                                    image.save()
                                    shopify_prod.image_id = image.id
                                    shopify_prod.save()

                                shopify_prod_rec.sudo().update(
                                    {'shopify_product_id': variant_id,
                                     'shopify_product_template_id': s_prod_tmpl_rec.id,
                                     'shopify_inventory_item_id': inventory_item_id,
                                     'last_updated_date': datetime.today().strftime(
                                         DEFAULT_SERVER_DATETIME_FORMAT)})
                                shopify_locations_records = self.env[
                                    'stock.location'].sudo().search(
                                    [('shopify_config_id', '=', config_id),
                                     ('shopify_location_id', '!=', False),
                                     ('usage', '=', 'internal'),
                                     ('shopify_legacy', '=', False)])
                                for shopify_locations_record in shopify_locations_records:
                                    shopify_location = shopify_locations_record.shopify_location_id
                                    shopify_location_id = shopify_locations_record.id
                                    available_qty = 0
                                    quant_locations = stock_quant_obj.sudo().search(
                                        [('location_id.usage', '=','internal'),
                                         ('product_id', '=',
                                            shopify_prod_rec.product_variant_id.id),
                                         ('location_id.shopify_location_id',
                                            'in', [shopify_location_id])])
                                    for quant_location in quant_locations:
                                        available_qty += quant_location.quantity
                                    if available_qty and shopify_prod_rec.update_shopify_inv:
                                        location = shopify.InventoryLevel.set(
                                            shopify_location,
                                            inventory_item_id,
                                            int(available_qty))
                        else:
                            error_msg = "Issue raised while exporting product variant!"
                            error_log_obj.create_update_log(
                                shop_error_log_id=shopify_log_id,
                                shopify_log_line_dict={
                                    'error': [{'error_message': error_msg}]})
                            continue
                    else:
                        error_msg = "Product template is created at Shopify, but not exported to Shopify. Kindly export a product template %s " % product_tmpl_id.name
                        error_log_obj.create_update_log(
                            shop_error_log_id=shopify_log_id,
                            shopify_log_line_dict={
                                'error': [{'error_message': error_msg}]})
                        continue
            else:
                error_msg = "A Product should be 'Can be Sold' before export %s" % (str(
                                product_tmpl_id.name))
                error_log_obj.create_update_log(
                    shop_error_log_id=shopify_log_id,
                    shopify_log_line_dict={
                        'error': [{'error_message': error_msg}]})
                continue


    def webhook_list_process(self, process):
        event_list = False
        if process == 'product':
            event_list = ["products/create"]
        if process == 'customer':
            event_list = ["customers/create"]
        if process == 'order':
            event_list = ["orders/create","orders/updated"]
        # if process == 'stock':
        #     event_list = ["inventory_levels/update"]
        return event_list


    def configure(self):
        self.shopify_product_webhook()
        self.shopify_customer_webhook()
        self.shopify_order_webhook()
        # self.shopify_stock_webhook()

    def shopify_product_webhook(self):
        event_list = self.webhook_list_process("product")
        self.configure_webhooks(event_list)

    def shopify_customer_webhook(self):
        event_list = self.webhook_list_process("customer")
        self.configure_webhooks(event_list)

    def shopify_order_webhook(self):
        event_list = self.webhook_list_process("order")
        self.configure_webhooks(event_list)

    # def shopify_stock_webhook(self):
    #     event_list = self.webhook_list_process("stock")
    #     self.configure_webhooks(event_list)

    def configure_webhooks(self, event_list):
        shopify_webhook = self.env["shopify.webhook"]
        resource = event_list[0].split('/')[0]
        shopify_config_id = self.id
        available_webhooks = shopify_webhook.search([("webhook_action", "in", event_list), ("shopify_config_id", "=", shopify_config_id)])
        if available_webhooks:
            available_webhooks.write({'active': True})
            _logger.info("{0} Webhooks are activated of instance '{1}'.".format(resource, self.name))
            event_list = list(set(event_list) - set(available_webhooks.mapped("webhook_action")))
        for event in event_list:
            webhook_id = shopify_webhook.create({"webhook_name": self.name + "_" + event.replace("/", "_"),
                                "webhook_action": event, "shopify_config_id":shopify_config_id,'active':True})
            if webhook_id.webhook_action == event:
                webhook_id.write({'callback_url':webhook_id.get_route()})
            _logger.info("Webhook for '{0}' of instance '{1}' created.".format(event, self.name))
    
    def webhook_delete(self):
        self._cr.execute("DELETE FROM shopify_webhook", log_exceptions=False)
        _logger.info("Webhook: Deleted")
        return True

    def action_update_product_qty_shopify(self):
        shopify_prod_obj = self.env['shopify.product.product']
        stock_quant_obj = self.env['stock.quant']
        location_env = self.env['stock.location']
        shopify_config = self.env['shopify.config'].sudo().search(
            [('state', '=', 'success'), ('default_company_id', '=', self.env.user.company_id.id)])
        # shopify_config.sudo().check_connection()
        shopify_prod_search = shopify_prod_obj.sudo().search(
            [('shopify_config_id', '=', shopify_config.id),
             ('update_shopify_inv', '=', True), ('product_variant_id.is_shopify_qty_changed', '=', True),('shopify_inventory_item_id','!=',False)])
        count = 1
        for prod in shopify_prod_search:
            shopify_config = prod.shopify_config_id
            shopify_config.sudo().check_connection()
            inventory_item_id = prod.shopify_inventory_item_id
            shopify_config_id = prod.shopify_config_id.id
            shopify_locations_records = location_env.sudo().search(
                [('shopify_config_id', '=', shopify_config.id), ('usage', '=', 'view'),
                 ('shopify_location_id', '!=', False)])
            f_qty = 0.0
            sh_location = ''
            sh_inv_item = ''
            for location_rec in shopify_locations_records:

                shopify_location = location_rec.shopify_location_id
                # shopify_location_id = location_rec.id
                product_variant_id = prod.product_variant_id
                qty_available = product_variant_id.with_context(
                    {'location': location_rec.id})._compute_quantities_dict(self._context.get('lot_id'),
                                                                            self._context.get('owner_id'),
                                                                            self._context.get('package_id'))
                variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
                shopify_location_id = location_rec.shopify_location_id
                shopify_inventory_item_id = prod.shopify_inventory_item_id
                f_qty += variant_qty
                sh_location = shopify_location_id
                sh_inv_item = shopify_inventory_item_id
                shopify.InventoryLevel.set(sh_location,
                                           sh_inv_item,
                                           int(f_qty))
                product_variant_id.is_shopify_qty_changed = False
            if count % 2 == 0:
                time.sleep(0.5)
            count += 1




        # error_log_env = self.env['shopify.error.log']
        # shopify_log_line_dict = {'error': [], 'success': []}
        # shopify_config = self.env['shopify.config'].sudo().search(
        #     [('state', '=', 'success'), ('default_company_id', '=', self.env.user.company_id.id)])
        # _logger.info(
        #     'Export Location------------------ "%s" inventory item id' % (
        #         shopify_config))
        # shopify_config.sudo().check_connection()
        # if shopify_config:
        #     location_ids = self.env['stock.location'].search(
        #         [('shopify_config_id', '=', shopify_config.id), ('usage', '=', 'view'),
        #          ('shopify_location_id', '!=', False)])
        #     if not location_ids:
        #         log_message = "location not found for shopify config %s " % self.name
        #         shopify_log_line_dict['error'].append(
        #             {'error_message': 'Export STOCK: %s' % log_message})
        #         return 0
        #     shopify_variant_id = self.env['shopify.product.product'].sudo().search(
        #         [('shopify_config_id', '=', shopify_config.id),
        #          ('update_shopify_inv', '=', True), ('product_variant_id.is_shopify_qty_changed', '=', True)])
        #     f_qty = 0.0
        #     sh_location = ''
        #     sh_inv_item = ''
        #     for location_id in location_ids:
        #         for sh_product in shopify_variant_id:
        #             product_variant_id = sh_product.product_variant_id
        #             if product_variant_id:
        #                 qty_available = product_variant_id.with_context(
        #                     {'location': location_id.id})._compute_quantities_dict(self._context.get('lot_id'),
        #                                                                            self._context.get('owner_id'),
        #                                                                            self._context.get('package_id'))
        #                 variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
        #                 shopify_location_id = location_id.shopify_location_id
        #                 shopify_inventory_item_id = sh_product.shopify_inventory_item_id
        #                 f_qty += variant_qty
        #                 sh_location = shopify_location_id
        #                 sh_inv_item = shopify_inventory_item_id
        #             product_variant_id.is_shopify_qty_changed = False
        #         if f_qty >= 0.0:
        #             shopify.InventoryLevel.set(sh_location,
        #                                        sh_inv_item,
        #                                        int(f_qty))
        #             _logger.info(
        #                 'Export stock successfully for location "%s" inventory item id "%s" : %s' % (
        #                     sh_location, sh_inv_item, f_qty))

    # def action_update_product_qty_shopify(self):
    #     variant_inv_sync = self.env['shopify.variant.inventory.sync']
    #     error_log_env = self.env['shopify.error.log']
    #     shopify_log_line_dict = {'error': [], 'success': []}
    #     shopify_config = self.env['shopify.config'].sudo().search(
    #         [('state', '=', 'success'), ('default_company_id', '=', self.env.user.company_id.id)])
    #     _logger.info(
    #         'Export Location------------------ "%s" inventory item id' % (
    #             shopify_config))
    #     shopify_config.sudo().check_connection()
    #     if shopify_config:
    #         shopify_variant_id = self.env['shopify.product.product'].sudo().search(
    #             [('shopify_config_id', '=', shopify_config.id),
    #              ('update_shopify_inv', '=', True), ('product_variant_id.is_shopify_qty_changed', '=', True)])
    #         for sh_product in shopify_variant_id:
    #             variant_id = variant_inv_sync.create({})
    #             variant_id.with_context({'active_ids':[sh_product.id]}).shopify_product_variant_inventory_sync()
    #
                # sh_product.shopify_product_variant_inventory_sync()

class ShopifyWorkflowLine(models.Model):
    _name = 'shopify.workflow.line'
    _description = 'Shopify Workflow Line'

    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    auto_workflow_id = fields.Many2one("shopify.workflow.process",
                                       "Auto Workflow")
    pay_gateway_id = fields.Many2one("shopify.payment.gateway", "Payment Gateway")
    financial_workflow_id = fields.Many2one("shopify.financial.workflow",
                                            "Financial Workflow")


class ShopifyTags(models.Model):

    _name = "shopify.tags"
    _description = "Shopify Tags"

    name = fields.Char('Name',required=True)

class shopifyInventoryqueue(models.Model):
    _name = 'shopify.inventory.queue'

    name = fields.Char('Name', readonly=True, index=True,
                       default=lambda self: _('New'))
    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    operation_type = fields.Selection([('update_stock','Update Stock')])
    state = fields.Selection([('draft', 'Draft'),
                              ('partial_processed', 'Partial Processed'),
                              ('processed', 'Processed'), ('failed', 'Failed')],
                             default='draft', string='Status',
                             # compute='_compute_queue_line_counts_and_state',
                             )
    queue_line_inventory_ids = fields.One2many("shopify.update.inventory.line",
                                          "shop_queue_inventory_id", string="Queue Lines")

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('name', _('New')) == _('New'):
                val['name'] = self.env['ir.sequence'].next_by_code(
                    'shopify.queue.job') or _('New')
        return super().create(vals)

    def update_inventory(self):
        self.shopify_config_id.check_connection()
        for rec in self.queue_line_inventory_ids:
            rec.shopify_config_id.with_user(self.env.user).update_shopify_inventory(shopify_location_id=rec.shopify_location_id, inventory_item_id=rec.shopify_inventory_item_id,
                                 qty=rec.variant_qty, shopify_log_id=False)

        self.state = 'processed'
        return True

class ShopifyInventoryUpdateLine(models.Model):
    _name = "shopify.update.inventory.line"
    _description = 'Shopify Queue Job Line'

    name = fields.Char(string="Name", required=True)
    state = fields.Selection([('draft', 'Draft'), ('processed', 'Processed'),
                              ("cancelled", "Cancelled"), ('failed', 'Failed')],
                             default='draft', string='Status')
    shop_queue_inventory_id = fields.Many2one("shopify.inventory.queue", string="Queue",
                                    ondelete='cascade')
    shopify_config_id = fields.Many2one(related='shop_queue_inventory_id.shopify_config_id',
                                        string='Shopify Configuration')
    # processed_date = fields.Datetime("Processed At", readonly=True)
    # record_data = fields.Text("Data", copy=False)
    shopify_location_id = fields.Char('Shopify Location')
    shopify_inventory_item_id = fields.Char('shopify_inventory_item')
    variant_qty = fields.Integer('Qty')
#
# class shopifyInventoryqueue(models.Model):
#     _name = 'shopify.inventory.queue'
#
#     name = fields.Char('Name', readonly=True, index=True,
#                        default=lambda self: _('New'))
#     shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
#                                         ondelete='cascade')
#     operation_type = fields.Selection([('update_stock','Update Stock')])
#     state = fields.Selection([('draft', 'Draft'),
#                               ('partial_processed', 'Partial Processed'),
#                               ('processed', 'Processed'), ('failed', 'Failed')],
#                              default='draft', string='Status',
#                              # compute='_compute_queue_line_counts_and_state',
#                              )
#     queue_line_inventory_ids = fields.One2many("shopify.update.inventory.line",
#                                           "shop_queue_inventory_id", string="Queue Lines")
#
#     @api.model_create_multi
#     def create(self, vals):
#         for val in vals:
#             if val.get('name', _('New')) == _('New'):
#                 val['name'] = self.env['ir.sequence'].next_by_code(
#                     'shopify.queue.job') or _('New')
#         return super().create(vals)
#
#     def update_inventory(self):
#         self.shopify_config_id.check_connection()
#         for rec in self.queue_line_inventory_ids:
#             rec.shopify_config_id.with_user(self.env.user).update_shopify_inventory(shopify_location_id=rec.shopify_location_id, inventory_item_id=rec.shopify_inventory_item_id,
#                                  qty=rec.variant_qty, shopify_log_id=False)
#
#         self.state = 'processed'
#         return True
#
# class ShopifyInventoryUpdateLine(models.Model):
#     _name = "shopify.update.inventory.line"
#     _description = 'Shopify Queue Job Line'
#
#     name = fields.Char(string="Name", required=True)
#     state = fields.Selection([('draft', 'Draft'), ('processed', 'Processed'),
#                               ("cancelled", "Cancelled"), ('failed', 'Failed')],
#                              default='draft', string='Status')
#     shop_queue_inventory_id = fields.Many2one("shopify.inventory.queue", string="Queue",
#                                     ondelete='cascade')
#     shopify_config_id = fields.Many2one(related='shop_queue_inventory_id.shopify_config_id',
#                                         string='Shopify Configuration')
#     # processed_date = fields.Datetime("Processed At", readonly=True)
#     # record_data = fields.Text("Data", copy=False)
#     shopify_location_id = fields.Char('Shopify Location')
#     shopify_inventory_item_id = fields.Char('shopify_inventory_item')
#     variant_qty = fields.Integer('Qty')