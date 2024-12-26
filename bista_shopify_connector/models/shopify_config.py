##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from .. import shopify
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import dateutil
from pytz import timezone
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import json
import requests

_shopify_allow_weights = ['kg', 'lb', 'oz', 'g']
_logger = logging.getLogger(__name__)


class ShopifyConfig(models.Model):
    _name = 'shopify.config'
    _description = 'Shopify Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _rec_name = 'name'

    def sale_based_on_month(self, rec):
        query = """SELECT to_char(date_order,'Month') as mon,
                    SUM(amount_total) as monthly_sum FROM sale_order sale 
                    WHERE sale.shopify_config_id = %s GROUP BY mon ORDER BY mon ASC""" % rec
        return query

    def sale_based_on_week(self, rec):
        query = """SELECT DATE_PART('Week',date_order) as week,
                    SUM(amount_total) as weekly_sum FROM sale_order sale 
                    WHERE sale.shopify_config_id = %s GROUP BY week ORDER BY week ASC""" % rec
        return query

    def sale_based_on_year(self, rec):
        query = """SELECT DATE_PART('Year',date_order) as year,
                    SUM(amount_total) as yearly_sum FROM sale_order sale 
                    WHERE sale.shopify_config_id = %s GROUP BY year ORDER BY year ASC""" % rec
        return query

    def return_query(self, rec):
        if rec.month_data == True:
            query = self.sale_based_on_month(rec.id)
            return query
        elif rec.week_data == True:
            query = self.sale_based_on_week(rec.id)
            return query
        elif rec.year_data == True:
            query = self.sale_based_on_year(rec.id)
            return query

    @api.depends('week_data', 'month_data', 'year_data')
    def compute_kanban_data(self):
        datas = []
        for rec in self:
            query = self.return_query(rec)
            self.env.cr.execute(query)
            query_results = self.env.cr.dictfetchall()
            if query_results:
                for result in query_results:
                    if rec.month_data == True:
                        datas.append({"value": result.get(
                            'monthly_sum'), "label": result.get('mon')})
                    elif rec.week_data == True:
                        datas.append({"value": result.get(
                            'weekly_sum'), "label": 'Week' + str(int(result.get('week')))})
                    elif rec.year_data == True:
                        datas.append({"value": result.get(
                            'yearly_sum'), "label": result.get('year')})
            else:
                datas = []
            rec.kanban_dashboard_graph = json.dumps(
                [{'values': datas, 'id': rec.id}])

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
                                             ('shopify_customer_id', '!=', False)])  # only consider main partners.

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

    kanban_dashboard_graph = fields.Text(
        compute="compute_kanban_data", help='This field computes the total sales data for kanban.')
    week_data = fields.Boolean('Week Data', default=True)
    month_data = fields.Boolean('Month Data', default=False)
    year_data = fields.Boolean('Year Data', default=False)
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
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse',
                                   help='Default warehouse which will be added to Sales Orders.')

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
                                           tracking=True, default="True",
                                           help='Import product images while importing products from Shopify.')
    # Commented to avoid recurring live sync from odoo to shopify when set to False.
    # When this boolean is False, User will have to manually click on 'Apply' button in stock quants and
    # this will update stock on shopify through live sync feature
    # is_validate_inv_adj = fields.Boolean(string='Validate Inventory Adjustment?',
    #                                      tracking=True,
    #                                      help='Whether to auto-validate inventory adjustment created during import stock operation.')
    is_pay_unearned_revenue = fields.Boolean(string='Do you want to go with unearned revenue payment flow?',
                                             tracking=True,
                                             help='Whether to add payment in Odoo as down-payment or normal payment.')
    is_use_shop_seq = fields.Boolean(string='Use Shopify Order Sequence?',
                                     tracking=True,
                                     help='If checked, Order will be created with Shopify order number else with Odoo default sequence.')
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
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist', help='Pricelist to be set on sales order.')
    shipping_product_id = fields.Many2one(
        'product.product', 'Shipping Product', help='Product used for Shopify Shipping charges.')
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Account',
                                          help='Analytic Account which will be added on Sales orders and Invoices imported through this configuration.')
    sale_team_id = fields.Many2one('crm.team', 'Sales Team',
                                   help='Sales team which will be selected on sales orders by default.')
    default_tax_account_id = fields.Many2one('account.account',
                                             'Tax Account',
                                             help="Tax account to be selected on Taxes(Repartition for Invoices) while creating new tax on import order operation.")
    default_tax_cn_account_id = fields.Many2one('account.account',
                                                'Tax Account on Credit Notes',
                                                help='Tax account to be selected on Taxes(Repartition for Credit Notes) while creating new tax on import order operation.')
    default_rec_account_id = fields.Many2one('account.account',
                                             'Receivable Account',
                                             help='Receivable account will be assigned to customers while importing customers.')
    default_pay_account_id = fields.Many2one(
        'account.account', 'Payable Account',
        help='Payable account will be assigned to customer s while importing customers.')
    unearned_account_id = fields.Many2one('account.account',
                                          'Unearned Revenue Account',
                                          help='Account which will be used on invoice when there is advance payment.')
    rounding_diff_account_id = fields.Many2one('account.account',
                                               'Rounding Difference Account',
                                               help='Account which will be used for rounding difference of imported orders')

    default_customer_id = fields.Many2one(
        'res.partner', 'Customer',
        help='Set a default customer which will be used when there is no customer on shopify orders.')
    default_payment_term_id = fields.Many2one(
        'account.payment.term', 'Payment Term',
        help='Default payment term to be added on sales order while importing sales order.')
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
    webhook_ids = fields.One2many(
        "shopify.webhook", "shopify_config_id", "Webhooks", context={'active_test': False})
    last_stock_export_date = fields.Datetime('Last Export Stock Date')
    last_refund_import_date = fields.Datetime('Last Import Refunds Date')
    last_return_order_import_date = fields.Datetime('Last Import Return Date')
    financial_workflow_ids = fields.One2many(
        'shopify.financial.workflow', 'shopify_config_id', string='Financial Workflow')
    # payout_ids = fields.One2many("shopify.payout.config", "shopify_config_id",
    #                                        string="Payouts")
    last_payout_import_date = fields.Datetime('Last Payout Import Date')
    shopify_tag_ids = fields.Many2many('shopify.tags', string='Shopify Tags')
    shopify_product_id = fields.Many2one(
        'product.product', 'Shopify Product', help='Product used if any odoo product is not found while sync.')
    is_create_customer = fields.Boolean(string='Create Customers?',
                                        tracking=True, default="True",
                                        help='If true will set a default customer which will be used when there is no customer on shopify orders.')
    product_categ_id = fields.Many2one(
        'product.category', 'Product Category', help='Product category used while sync.', tracking=True)
    shopify_location_mappings = fields.One2many('shopify.location.mapping', 'shopify_config_id',
                                                string="Shopify Odoo Location Mapping"
                                                )
    invoicing_policy = fields.Selection([('order', 'Ordered Quantities'),
                                         ('delivery', 'Delivered Quantities')],
                                        string='Invoicing Policy')
    sync_inventory_on_reservation = fields.Boolean(
        string="Sync Inventory on Reservation")

    fiscal_shopify_id= fields.Many2one('account.fiscal.position', string='Fiscal Position Shopify ')
    default_payment_journal_id = fields.Many2one('account.journal', string='Default Payment Journal',
                                                 domain=[('type', 'in', ['cash', 'bank'])])


    def get_update_value_from_config(self, operation='read', field='', shopify_config_id=False, field_value='', parameter_id=False):
        if not parameter_id and not field_value and shopify_config_id and operation == 'read':
            key_name = 'shopify_config_%s' % (str(self.id))
            parameter_id = self.env['ir.config_parameter'].search([('key', '=', key_name)])
            value2 = parameter_id.value
            dict = eval(value2)
            if field:
                date_value = ''
                if operation == 'read':
                    date_value = dict.get(field)
                    if date_value:
                        date_value = datetime.strptime(date_value, '%Y/%m/%d %H:%M:%S')
                return date_value, parameter_id

        else:
            value2 = parameter_id.value
            dict = eval(value2)
            dict[field] = field_value
            parameter_id.write({'value': dict})

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if self.warehouse_id == False:
            self.warehouse_id.shopify_config_id = False
        else:
            warehouse_id = self.env['stock.warehouse'].search(
                [('shopify_config_id', '=', self._origin.id)], limit=1)
            if warehouse_id and warehouse_id.id != self.warehouse_id.id:
                self.warehouse_id.shopify_config_id = self._origin or self.id
                warehouse_id.shopify_config_id = False

    def import_export_data(self):
        """Import/Export data from/to Shopify."""
        context = self._context
        # check connection state
        for t_con in self.search(
                [('state', '!=', 'success'), ('active', '=', True)]):
            t_con.check_connection()
        for config in self.search(
                [('state', '=', 'success'), ('active', '=', True)]):
            if context.get('from_cust'):
                self.env['res.partner'].with_delay(description="Import All Customer",
                                                   max_retries=5).shopify_import_customers(config)
            elif context.get('from_order'):
                self.env['sale.order'].with_delay(description="Import All Orders",
                                                  max_retries=5).shopify_import_orders(config)
            elif context.get('from_location'):
                self.env['stock.location'].with_delay(description="Import Locations",
                                                      max_retries=5).shopify_import_location(config)
            elif context.get('from_collection'):
                self.env[
                    'shopify.product.collection'].with_delay(description="Import All Collections",
                                                             max_retries=5).shopify_import_product_collection(
                    config)
            elif context.get('export_collection'):
                self.env[
                    'shopify.product.collection'].with_delay(description="Export Collections",
                                                             max_retries=5).shopify_export_product_collection(
                    config)
            elif context.get('export_product'):
                config.with_delay(description="Export Products",
                                  max_retries=5).export_products_to_shopify()
            elif context.get('update_product'):
                config.with_delay(description="Update Products to Shopify",
                                  max_retries=5).update_products_to_shopify()
            elif context.get('export_stock'):
                config.with_delay(description="Export Stock",
                                  max_retries=5).export_stock_to_shopify()
            elif context.get('import_product'):
                self.env['shopify.product.template'].with_delay(description="Import All Products",
                                                                max_retries=5).shopify_import_product(
                    config)
            elif context.get('from_refund'):
                self.env['account.move'].with_delay(description="Import Refunds",
                                                    max_retries=5).shopify_import_refund_orders(config)
            elif context.get('from_order_status'):
                self.env['sale.order'].with_delay(description="Export Order Status",
                                                  max_retries=5).shopify_update_order_status(config)
            elif context.get('from_stock'):
                self.env['shopify.product.template'].with_delay(description="Import Stock",
                                                                max_retries=5).shopify_import_stock(config)

    def shopify_archive_active(self):
        """This method will set the shopify config to archive/active"""
        if self.active:
            [webhook.write({'active': False}) for webhook in self.webhook_ids]
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
        module_sale_enterprise = self.env['ir.module.module'].sudo().search([
            ('name', '=', 'sale_enterprise'),
            ('state', '=', 'installed')], limit=1)
        if not module_sale_enterprise:
            action = self.env.ref(
                'bista_shopify_connector.shopify_sale_order_action').sudo().read()[0]
        else:
            action = self.env.ref(
                'sale_enterprise.sale_report_action_dashboard').sudo().read()[0]
            action['domain'] = [('order_id.shopify_config_id', '=', self.id)]
        return action

    def action_shopify_queue_operations(self):
        """ This method will redirect to shopify queue operations"""
        self.ensure_one()
        action = self.env.ref(
            'bista_shopify_connector.action_shopify_log_lines').sudo().read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_log_operations(self):
        """ This method will redirect to shopify log operations"""
        self.ensure_one()
        action = self.env.ref(
            'bista_shopify_connector.action_shopify_error_log').sudo().read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def action_wizard_shopify_import_export_operations(self):
        """ This method will show shopify operation actions"""
        self.ensure_one()
        action = self.env.ref(
            'bista_shopify_connector.action_wizard_shopify_import_export_operations').sudo().read()[0]
        action['context'] = {'default_shopify_config_id': self.id}
        return action

    def action_shopify_customer(self):
        """ This method will show shopify customer actions"""
        self.ensure_one()
        action = self.env.ref('base.action_partner_form').sudo().read()[0]
        action['domain'] = [('parent_id', '=', False),
                            ('shopify_config_id', '=', self.id),
                            ('shopify_customer_id', '!=', False)]
        return action

    def action_shopify_product(self):
        """ This method will show shopify product actions"""
        self.ensure_one()
        action = self.env.ref('product.product_template_action_all').sudo().read()[0]
        action['domain'] = [
            ('shopify_product_template_ids.shopify_config_id', '=', self.id)]
        return action

    def action_shopify_order(self):
        """ This method will show shopify orders actions"""
        self.ensure_one()
        action = self.env.ref('sale.action_orders').sudo().read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_invoice(self):
        """ This method will show shopify invoice actions"""
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        action['domain'] = [('move_type', '=', 'out_invoice'),
                            ('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_credit_note(self):
        """ This method will show shopify credit note actions"""
        self.ensure_one()
        action = self.env.ref('account.action_move_out_refund_type').sudo().read()[0]
        action['domain'] = [('move_type', '=', 'out_refund'),
                            ('shopify_config_id', '=', self.id)]
        return action

    def action_shopify_delivery(self):
        """ This method will show shopify delivery actions"""
        self.ensure_one()
        action = self.env.ref("stock.action_picking_tree_all").sudo().read()[0]
        action['domain'] = [('picking_type_id.code', '=',
                             'outgoing'), ('shopify_config_id', '=', self.id)]
        return action

    def action_active_locations(self):
        """ This method will show shopify delivery actions"""
        self.ensure_one()
        action = self.env.ref("stock.action_location_form").sudo().read()[0]
        action['domain'] = [('shopify_config_id', '=', self.id)]
        return action

    def schedulers_configuration_action(self):
        """ This method will show shopify scheduler actions"""
        self.ensure_one()
        action = self.env.ref('base.ir_cron_act').sudo().read()[0]
        action['domain'] = ['|', ('name', 'ilike', self.name),
                            ('name', 'ilike', 'shopify')]
        return action

    def action_active_schedulers(self):
        """ This method will show shopify avtive scheduler actions"""
        self.ensure_one()
        action = self.env.ref('base.ir_cron_act').sudo().read()[0]
        action['domain'] = ['|', ('name', 'ilike', self.name),
                            ('name', 'ilike', 'shopify'), ('active', '=', True)]
        return action

    def reset_to_draft(self):
        """ This method will set the shopify config to draft state """
        [webhook.write({'active': False}) for webhook in self.webhook_ids]
        self.update({'state': 'draft'})

    def convert_shopify_datetime_to_utc(self, date):
        converted_datetime = ""
        if date:
            shop_date = dateutil.parser.parse(date)
            converted_datetime = shop_date.astimezone(timezone('UTC')).strftime(
                '%Y-%m-%d %H:%M:%S')
        return converted_datetime or False

    def check_connection_button(self):
        """
        This function check that shopify store is exist or not using api_key,
        password and shop_url using the button
        """
        for rec in self:
            ir_config_obj = self.env['ir.config_parameter']
            if rec.active:
                try:
                    api_key = rec.api_key or ''
                    password = rec.password or ''
                    shop_url = rec.shop_url and "%s/admin" % rec.shop_url or ''
                    if api_key and password and shop_url:
                        shopify.ShopifyResource.set_user(api_key)
                        shopify.ShopifyResource.set_password(password)
                        shopify.ShopifyResource.set_site(shop_url)
                        shop = shopify.Shop.current()
                        if shop and rec.state != 'success':
                            rec.update({'state': 'success',
                                        'shopify_shop_id': rec.shopify_shop_id,
                                        'shopify_shop_name': rec.shopify_shop_name,
                                        'shopify_shop_currency': rec.shopify_shop_currency,
                                        'shopify_shop_owner': rec.shopify_shop_owner,
                                        'timezone': rec.timezone,
                                        'timezone_name': rec.timezone_name})
                            key = 'shopify_config_%s' % (str(rec.id))
                            config_id = ir_config_obj.search([
                                ('key', '=', key)], limit=1)
                            if not config_id:
                                value = {
                                    'last_import_order_date': '',
                                    'last_import_customer_date': '',
                                    'last_product_import_date': '',
                                    'last_stock_import_date': '',
                                    'last_stock_export_date': '',
                                    'last_refund_import_date': '',
                                    'last_return_order_import_date': '',
                                    'last_payout_import_date': '',
                                    'last_collection_import_date': ''
                                }
                                ir_config_obj.create({'key': key, 'value': value})

                        elif not shop:
                            rec.update({'state': 'fail'})
                    else:
                        rec.update({'state': 'fail'})
                        self._cr.commit()
                        _logger.error('Invalid API key or access token.')
                except Exception as e:
                    rec.update({'state': 'fail'})
                    self._cr.commit()
                    _logger.error('Invalid API key or access token: %s', e)
            else:
                _logger.error('%s Instance is deactivated,please \
                        activate to process sync.', rec.name)

    def check_connection(self):
        """
        This function check that shopify store is exist or not using api_key,
        password and shop_url
        """
        for rec in self:
            if rec.active and rec.state == 'success':
                try:
                    api_key = rec.api_key or ''
                    password = rec.password or ''
                    shop_url = rec.shop_url and "%s/admin" % rec.shop_url or ''
                    if api_key and password and shop_url:
                        shopify.ShopifyResource.set_user(api_key)
                        shopify.ShopifyResource.set_password(password)
                        shopify.ShopifyResource.set_site(shop_url)
                        shopify.Shop.current()
                except Exception as e:
                    _logger.error('Invalid API key or access token: %s', e)
            else:
                _logger.error('%s Instance is deactivated,please \
                        activate to process sync.', rec.name)

    def export_stock_to_shopify(self):
        """
        Export stock odoo to shopify
        """

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Export Stock",
            'shopify_config_id': self.id,
            'operation_type': 'export_stock',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        parameter_stock_id = self.env['ir.config_parameter'].search(
            [('key', '=', 'shopify.stock.export.zero.qty')])

        try:
            # error_log_env = self.env['shopify.error.log']
            shopify_log_line_obj = self.env['shopify.log.line']
            # shopify_log_id = error_log_env.create_update_log(
            #     shopify_config_id=self,
            #     operation_type='export_stock')
            shopify_log_line_dict = {'error': [], 'success': []}
            self.check_connection()
            mapping_location_ids = self.env['shopify.location.mapping'].search(
                [('shopify_config_id', '=', self.id),
                 ('shopify_location_id', '!=', False), ('odoo_location_id', '!=', False)])
            if not mapping_location_ids:
                log_message = "location not found for shopify config %s " % self.name
                shopify_log_line_dict['error'].append(
                    {'error_message': 'Export STOCK: %s' % log_message})
                return False
            shopify_product_variants = self.env['shopify.product.product'].sudo().search(
                [('shopify_config_id', '=', self.id),
                 ('update_shopify_inv', '=', True)])
            seconds = 30
            for location_id in mapping_location_ids:
                if not mapping_location_ids:
                    log_message = "Location not found for shopify config %s " % self.name
                    shopify_log_line_dict['error'].append(
                        {'error_message': 'Export stock: %s' % log_message})
                    return False
                for shopify_variant_id in shopify_product_variants:
                    product_variant_id = shopify_variant_id.product_variant_id
                    if product_variant_id.detailed_type == 'product' and not shopify_variant_id.shopify_inventory_item_id:
                        log_message = "Inventory item ID not found for Product Variant %s in export stock." % product_variant_id.name
                        shopify_log_line_dict['error'].append(
                            {'error_message': 'Export stock: %s' % log_message})
                        continue
                    # qty_available = product_variant_id.with_context(
                    #     {'location': location_id.id})._product_available()
                    if product_variant_id.detailed_type == 'service':
                        continue
                    qty_available = product_variant_id.with_context({
                        'location': location_id.odoo_location_id.id
                    })._compute_quantities_dict(
                        self._context.get('lot_id'), self._context.get('owner_id'),
                        self._context.get('package_id'))
                    variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
                    if (parameter_stock_id and parameter_stock_id.value ==
                        'False') and variant_qty == 0:
                        continue
                    shopify_location_id = location_id.shopify_location_id
                    # shopify_inventory_item_id = shopify_variant_id.shopify_inventory_item_id

                    name = "%s - %s" % (location_id.odoo_location_id.display_name,
                                        shopify_variant_id.product_variant_id.display_name)
                    job_descr = _("Export Stock to shopify: %s") % (name and name.strip())

                    log_line_id = shopify_log_line_obj.create({
                        'name': job_descr,
                        'shopify_config_id': self.id,
                        'id_shopify': f"Location: {shopify_location_id or ''} Product: {shopify_variant_id.shopify_product_id}",
                        'operation_type': 'export_stock',
                        'parent_id': parent_log_line_id.id
                    })
                    eta = datetime.now() + timedelta(seconds=seconds)
                    self.with_company(self.default_company_id).with_delay(description=job_descr, max_retries=5, eta=eta).export_stock(shopify_location_id,
                                                                                                shopify_variant_id,
                                                                                                int(variant_qty),
                                                                                                log_line_id)
                    seconds += 2
                # self.last_stock_export_date = fields.Datetime.now()
                key_name = 'shopify_config_%s' % (str(self.id))
                parameter_id = self.env['ir.config_parameter'].search([('key', '=', key_name)])
                self.get_update_value_from_config(
                    operation='write', field='last_stock_export_date', shopify_config_id=self,
                    field_value=str(datetime.now().strftime('%Y/%m/%d %H:%M:%S')), parameter_id=parameter_id)

                # error_log_env.create_update_log(shopify_config_id=self,
                #                                 shop_error_log_id=shopify_log_id,
                #                                 shopify_log_line_dict=shopify_log_line_dict)
                # if not shopify_log_id.shop_error_log_line_ids:
                #     shopify_log_id.unlink()
            if len(shopify_log_line_dict['error']):
                parent_log_line_id.update({
                    'state': 'error',
                    'message': shopify_log_line_dict['error'],
                })
            else:
                parent_log_line_id.update({
                    'state': 'success',
                    'message': 'Operation Successful'
                })
            return True
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def export_stock(self, shopify_location_id, shopify_variant_id, variant_qty, log_line_id):
        shopify_inventory_item_id = shopify_variant_id.shopify_inventory_item_id
        try:
            base_url = self.shop_url
            data = {"location_id": int(shopify_location_id),
                    "inventory_item_id": int(shopify_inventory_item_id),
                    "available":int(variant_qty)}
            api_order_url = "/admin/api/2024-01/inventory_levels/set.json"
            url = base_url + api_order_url
            headers = {'X-Shopify-Access-Token': self.password,
                       'Content-Type': 'application/json'}
            response = requests.request(
                'POST', url, headers=headers, data=json.dumps(data))
            response = response.json()
            if not response.get('errors'):
                product_id = shopify_variant_id.product_variant_id
                odoo_location_id = self.shopify_location_mappings.filtered(
                    lambda l: l.shopify_location_id == shopify_location_id).odoo_location_id
                quant = self.env['stock.quant'].search(
                    [('location_id', '=', odoo_location_id.id),
                     ('product_id', '=', product_id.id)], limit=1)
                log_line_id.update({
                    'state': 'success',
                    'related_model_name': 'stock.quant',
                    'related_model_id': quant.id,
                    'message': 'Operation Successful'
                })
            else:
                raise ValidationError(
                    _("Request did not competed due to: %s"%(str(
                        response.get('errors')))))
        except Exception as e:
            log_line_id.update({
                'state': 'error',
                'message': 'Failed to export Stock : {}'.format(e)
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def update_shopify_inventory(self, shopify_location_id, inventory_item_id,
                                 qty, log_line_id, adjustment=False):
        """
        Adjust qty on shopify base on given location_id and inventory_item_id
        """
        self.ensure_one()
        self.check_connection()
        try:
            if adjustment:
                shopify.InventoryLevel.adjust(shopify_location_id,
                                              inventory_item_id, qty)
            else:
                shopify.InventoryLevel.set(
                    shopify_location_id, inventory_item_id, available=qty)
            _logger.info('Export stock successfully for location "%s" inventory item id "%s" : %s' % (
                shopify_location_id, inventory_item_id, qty))
            log_line_id.write({'state': 'success'})
        except Exception as e:
            log_line_id.write({'state': 'error',
                               'message': e})

    def update_products_to_shopify(self):
        """
        update a product template data to shopify which need to be updated on
        shopify.
        """

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Update Products",
            'shopify_config_id': self.id,
            'operation_type': 'update_product',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            self.ensure_one()
            shopify_log_line_obj = self.env['shopify.log.line']
            user_id = self.env.user.id
            product_tmpl_ids = self.env['shopify.product.template'].with_user(
                user_id).search(
                [('shopify_config_id', '=', self.id),
                 ('shopify_prod_tmpl_id', '!=', False),
                 ('ready_to_update', '=', True)])
            seconds = 30
            for prod_tmpl in product_tmpl_ids:
                name = prod_tmpl.product_tmpl_id.display_name or ''
                eta = datetime.now() + timedelta(seconds=seconds)
                job_descr = _("Update Product to Shopify: %s") % (
                        name and name.strip())
                log_line_id = shopify_log_line_obj.create({
                    'name': job_descr,
                    'shopify_config_id': self.id,
                    'id_shopify': prod_tmpl.shopify_prod_tmpl_id or '',
                    'operation_type': 'update_product',
                    'parent_id': parent_log_line_id.id
                })
                prod_tmpl.with_company(
                    prod_tmpl.shopify_config_id.default_company_id).with_delay(
                    description=job_descr, max_retries=5,
                    eta=eta).update_product_to_shopify(
                    prod_tmpl.shopify_config_id, log_line_id=log_line_id)
                seconds += 2
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def export_products_to_shopify(self):
        """
        Fetch a product template ids which need to be updated on shopify
        and pass it to the export_product
        """

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Export Products",
            'shopify_config_id': self.id,
            'operation_type': 'export_product',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            self.ensure_one()
            shopify_log_line_obj = self.env['shopify.log.line']
            user_id = self.env.user.id
            product_tmpl_ids = self.env['shopify.product.template'].with_user(
                user_id).search(
                [('shopify_config_id', '=', self.id),
                 ('shopify_prod_tmpl_id', 'in', ['', False])])
            seconds = 30
            for prod_tmpl in product_tmpl_ids:
                name = prod_tmpl.product_tmpl_id.display_name or ''
                job_descr = _("Export Product to Shopify:   %s") % (
                        name and name.strip())
                eta = datetime.now() + timedelta(seconds=seconds)
                log_line_id = shopify_log_line_obj.create({
                    'name': job_descr,
                    'shopify_config_id': self.id,
                    'id_shopify': prod_tmpl.shopify_prod_tmpl_id or '',
                    'operation_type': 'export_product',
                    'parent_id': parent_log_line_id.id
                })
                self.with_company(self.default_company_id).with_delay(
                    description=job_descr, max_retries=5,
                    eta=eta).export_product(prod_tmpl, log_line_id=log_line_id)
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
        except Exception as e:
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

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
            price = self.pricelist_id._get_product_price(product,
                                                        1.0,
                                                        uom=product.uom_id)

            if product.default_code or product.barcode:
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
                        'barcode': product.barcode or "",
                        'inventory_management': 'shopify' if s_product.shopify_inventory_management else None,
                        'inventory_policy': 'continue' if s_product.shopify_inventory_policy else 'deny',
                        'cost': product.standard_price
                    })
                variants += [variant_val]
        return variants

    def export_product(self, s_product_tmpl_ids,
                       shopify_locations_records=False, log_line_id=False):
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
        self.ensure_one()
        shopify_config_id = self
        shopify_config_id.check_connection()
        shopify_prod_obj = self.env['shopify.product.product']

        stock_quant_obj = self.env['stock.quant']
        mapping_locations = self.env['shopify.location.mapping']

        # Fetch Locations based on the shopify configuration
        if not mapping_locations:
            shopify_locations_records = mapping_locations.with_user(self.env.user).search(
                [('shopify_config_id', '=', shopify_config_id.id),
                 ('shopify_location_id', '!=', False),
                 ('odoo_location_id', '!=', False),
                 ('odoo_location_id.usage', '=', 'internal'),
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
                    products = shopify_prod_obj.with_user(self.env.user). \
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
                        raise ValidationError(_(error_msg))
                else:
                    error_msg = "A Product %s should be 'Can be Sold' before export" % (str(
                        product_tmpl_id.name))
                    raise ValidationError(_(error_msg))
                    # error_log_obj.create_update_log(
                    #     shop_error_log_id=shopify_log_id,
                    #     shopify_log_line_dict={
                    #         'error': [
                    #             {'error_message': error_msg}]})
                    # continue

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
                success = new_product.save()
                # returns false if the record is invalid
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
                            s_product_tmpl_id.product_tmpl_id.update({
                                'export_status': 'exported'
                            })
                            # Get shopify variant vals using shopify create
                            # recordset
                            for variant in new_product.variants:
                                variant_id = variant.id

                                inventory_item_id = variant.inventory_item_id
                                default_code = variant.sku
                                barcode = variant.barcode
                                shopify_product_product = shopify_prod_obj.with_user(self.env.user). \
                                    search([('shopify_config_id', '=', shopify_config_id.id),
                                            ('shopify_product_id',
                                             'in', ['', False]),
                                            ('product_template_id',
                                             '=', product_tmpl_id.id),
                                            '|',
                                            ('default_code', '=', default_code),
                                            ('barcode', '=', barcode)], limit=1)
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
                                    shopify_product_product.with_user(self.env.user).update(
                                        {'shopify_product_id': variant_id,
                                         'shopify_product_template_id': s_product_tmpl_id.id,
                                         'shopify_inventory_item_id': inventory_item_id,
                                         'last_updated_date': datetime.today().strftime(
                                             DEFAULT_SERVER_DATETIME_FORMAT)})
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
                                        # if available_qty and shopify_product_product.update_shopify_inv:
                                        if shopify_product_product.update_shopify_inv:
                                            shopify.InventoryLevel.set(
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
                        error_msg = 'Facing a problems while exporting product! %s' % str(e)
                        raise ValidationError(_(error_msg))
                log_line_id.update({
                    'state': 'success',
                    'id_shopify': new_product.id
                })
            except Exception as e:
                _logger.error(
                    _('Facing a problems while exporting product!: %s') % e)
                error_msg = 'Facing a problems while exporting product!: %s' % str(e)
                log_line_id.update({
                    'state': 'error',
                    'message': error_msg
                })
                self.env.cr.commit()
                raise UserError(_(error_msg))

    def export_prod_variant(self, shopify_prod_rec, log_line_id=False):
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
        get_param = self.env['ir.config_parameter'].sudo().get_param
        prod_weight_unit = get_param('product.weight_in_lbs')

        if prod_weight_unit == '1':
            weight_unit = self.env.ref('uom.product_uom_lb')
        else:
            weight_unit = self.env.ref('uom.product_uom_kgm')
        for rec in self:
            try:
                rec.check_connection()
                config_id = rec.id
                if shopify_prod_rec.shopify_product_id:
                    name = shopify_prod_rec.product_variant_id.name
                    error_msg = "Variant %s is already exported to Shopify." % (
                        name)
                    raise ValidationError(_(error_msg))
                product = shopify_prod_rec.product_variant_id
                product_tmpl_id = product.product_tmpl_id
                options_dict = {}
                option_count = 0

                if (shopify_prod_rec.shopify_product_template_id and
                        shopify_prod_rec.shopify_product_template_id.shopify_prod_tmpl_id):
                    product_template_dict = shopify.Product().find(
                        shopify_prod_rec.shopify_product_template_id.shopify_prod_tmpl_id)
                    product_template_dict = product_template_dict.to_dict()
                    if product_template_dict.get('options'):
                        for opt in product_template_dict.get('options'):
                            options_dict.update({opt.get('name'): opt.get(
                                'position')})
                            option_count = len(options_dict)

                if product_tmpl_id.sale_ok:
                    s_prod_tmpl_rec = s_prod_tmpl.sudo().search(
                        [('product_tmpl_id', '=', product_tmpl_id.id),
                         ('shopify_config_id', '=', config_id)], limit=1)
                    if not s_prod_tmpl_rec:
                        error_msg = "'Shopify Product template %s record is not " \
                                    "found. Kindly export a product template'" % (
                                        product_tmpl_id.name)
                        raise ValidationError(_(error_msg))
                    else:
                        shopify_prod_tmpl_id = s_prod_tmpl_rec.shopify_prod_tmpl_id
                        if shopify_prod_tmpl_id:
                            shopify_prod = shopify.Variant()
                            count = 1
                            for value in product.product_template_attribute_value_ids:
                                opt_cmd = 'shopify_prod.option' + str(
                                    count) + " = '" + str(value.name) + "'"
                                if options_dict and options_dict.get(value.attribute_id.name):
                                    opt_cmd = 'shopify_prod.option' + str(
                                        options_dict.get(value.attribute_id.name)) + " = '" + str(value.name) + "'"
                                exec(opt_cmd)
                                count += 1
                            if weight_unit and weight_unit.name in _shopify_allow_weights:
                                shopify_prod.weight = product.weight
                                shopify_prod.weight_unit = weight_unit.name
                            else:
                                _logger.error(
                                    _('UOM is not define for product variant id!: %s') % str(
                                        product.id))
                            res = product.taxes_id.compute_all(
                                product.lst_price, product=product, partner=self.env['res.partner'])
                            price = res['total_included']
                            shopify_prod.price = price or shopify_prod_rec.product_variant_id.lst_price or '0.00'
                            shopify_prod.inventory_management = 'shopify' if shopify_prod_rec.shopify_inventory_management else None
                            shopify_prod.inventory_policy = 'continue' if shopify_prod_rec.shopify_inventory_policy else 'deny'
                            shopify_prod.cost = shopify_prod_rec.product_variant_id.standard_price
                            if rec.sync_product == 'sku':
                                if product.default_code:
                                    shopify_prod.sku = product.default_code
                                else:
                                    error_msg = "Please set Internal reference for " \
                                                "product variant %s before exporting to shopify !" % (
                                                    product.name)
                                    raise ValidationError(_(error_msg))
                            elif rec.sync_product == 'barcode':
                                if product.barcode:
                                    shopify_prod.barcode = product.barcode
                                else:
                                    error_msg = "Please set Barcode for " \
                                                "product variant %s before exporting to shopify !" % (
                                                    product.name)
                                    raise ValidationError(_(error_msg))
                            else:
                                if product.barcode or product.default_code:
                                    shopify_prod.barcode = product.barcode
                                    shopify_prod.sku = product.default_code
                                else:
                                    error_msg = "Please set Barcode or Internal Reference for " \
                                                "product variant %s before exporting to shopify !" % (
                                                    product.name)
                                    raise ValidationError(_(error_msg))
                            shopify_prod.inventory_management = "shopify"
                            shopify_prod.product_id = shopify_prod_tmpl_id
                            shopify_prod.cost = product.standard_price
                            # if 'inventory_quantity' in shopify_prod.attributes:
                            #     del shopify_prod.attributes["inventory_quantity"]
                            # if 'old_inventory_quantity' in shopify_prod.attributes:
                            #     del shopify_prod.attributes["old_inventory_quantity"]
                            # if 'inventory_quantity_adjustment' in shopify_prod.attributes:
                            #     del shopify_prod.attributes["inventory_quantity_adjustment"]
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
                                    if 'inventory_quantity' in shopify_prod.attributes:
                                        del shopify_prod.attributes["inventory_quantity"]
                                    if 'old_inventory_quantity' in shopify_prod.attributes:
                                        del shopify_prod.attributes["old_inventory_quantity"]
                                    if 'inventory_quantity_adjustment' in shopify_prod.attributes:
                                        del shopify_prod.attributes["inventory_quantity_adjustment"]
                                    shopify_prod_rec.sudo().update(
                                        {'shopify_product_id': variant_id,
                                         'shopify_product_template_id': s_prod_tmpl_rec.id,
                                         'shopify_inventory_item_id': inventory_item_id,
                                         'last_updated_date': datetime.today().strftime(
                                             DEFAULT_SERVER_DATETIME_FORMAT)})
                                    shopify_location_mappings = self.env['shopify.location.mapping'].search(
                                        [('shopify_location_id', '!=', False),
                                         ('odoo_location_id', '!=', False),
                                         ('shopify_config_id', '=', rec.id)])
                                    # shopify_locations_records = shopify_location_mappings.mapped('odoo_location_id')
                                    for shopify_locations_record in shopify_location_mappings:
                                        shopify_location = shopify_locations_record.shopify_location_id
                                        odoo_location_id = shopify_locations_record.odoo_location_id.id
                                        all_locations = self.env['stock.location'].search(
                                            [('id', 'child_of', odoo_location_id)]).ids
                                        available_qty = 0
                                        quant_locations = stock_quant_obj.sudo().search(
                                            [('location_id.usage', '=', 'internal'),
                                             ('product_id', '=',
                                              shopify_prod_rec.product_variant_id.id),
                                             ('location_id',
                                              'in', all_locations)])
                                        for quant_location in quant_locations:
                                            available_qty += quant_location.quantity
                                        # if available_qty and shopify_prod_rec.update_shopify_inv:
                                        if shopify_prod_rec.update_shopify_inv:
                                            location = shopify.InventoryLevel.set(
                                                shopify_location,
                                                inventory_item_id,
                                                int(available_qty))
                            else:
                                error_msg = "Issue raised while exporting product variant!"
                                raise ValidationError(_(error_msg))
                        else:
                            error_msg = "Product template is created at Shopify, but not exported to Shopify. Kindly export a product template %s " % product_tmpl_id.name
                            raise ValidationError(_(error_msg))
                else:
                    error_msg = "A Product should be 'Can be Sold' before export %s" % (str(
                        product_tmpl_id.name))
                    raise ValidationError(_(error_msg))
                log_line_id.update({
                    'state': 'success',
                })
            except Exception as e:
                _logger.error(
                    _('Facing a problems while exporting product variant!: %s')
                    % e)
                error_msg = ('Facing a problems while exporting product '
                             'variant!: %s' % e)
                log_line_id.update({
                    'state': 'error',
                    'message': error_msg
                })
                self.env.cr.commit()
                raise UserError(_(e))

    def webhook_list_process(self, process):
        event_list = False
        if process == 'product':
            event_list = ["products/create"]
        if process == 'customer':
            event_list = ["customers/create"]
        if process == 'order':
            event_list = ["orders/create", "orders/updated"]
        # if process == 'stock':
        #     event_list = ["inventory_levels/update"]
        if process == 'collections':
            event_list = ["collections/updated"]
        return event_list

    def configure(self):
        self.shopify_product_webhook()
        self.shopify_customer_webhook()
        self.shopify_order_webhook()
        self.shopify_collection_webhook()
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

    def shopify_collection_webhook(self):
        event_list = self.webhook_list_process("collections")
        self.configure_webhooks(event_list)

    # def shopify_stock_webhook(self):
    #     event_list = self.webhook_list_process("stock")
    #     self.configure_webhooks(event_list)

    def configure_webhooks(self, event_list):
        self.update_webhooks()
        shopify_webhook = self.env["shopify.webhook"]
        resource = event_list[0].split('/')[0]
        shopify_config_id = self.id
        available_webhooks = shopify_webhook.search(
            [("webhook_action", "in", event_list), ("shopify_config_id", "=", shopify_config_id)])
        if available_webhooks:
            available_webhooks.write({'active': True})
            _logger.info("{0} Webhooks are activated of instance '{1}'.".format(
                resource, self.name))
            event_list = list(set(event_list) -
                              set(available_webhooks.mapped("webhook_action")))
        for event in event_list:
            webhook_id = shopify_webhook.create({"webhook_name": self.name + "_" + event.replace("/", "_"),
                                                 "webhook_action": event, "shopify_config_id": shopify_config_id,
                                                 'active': True})
            if webhook_id.webhook_action == event:
                webhook_id.write({'callback_url': webhook_id.get_route()})
            _logger.info(
                "Webhook for '{0}' of instance '{1}' created.".format(event, self.name))

    def update_webhooks(self):
        if self.webhook_ids and self.state == 'success':
            [webhook.write({'active': True}) for webhook in self.webhook_ids]

    def webhook_delete(self):
        self._cr.execute("DELETE FROM shopify_webhook", log_exceptions=False)
        _logger.info("Webhook: Deleted")
        return True


class ShopifyWorkflowLine(models.Model):
    _name = 'shopify.workflow.line'
    _description = 'Shopify Workflow Line'

    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    auto_workflow_id = fields.Many2one("shopify.workflow.process",
                                       "Auto Workflow")
    pay_gateway_id = fields.Many2one(
        "shopify.payment.gateway", "Payment Gateway")
    financial_workflow_id = fields.Many2one("shopify.financial.workflow",
                                            "Financial Workflow")


class ShopifyTags(models.Model):
    _name = "shopify.tags"
    _description = "Shopify Tags"

    name = fields.Char('Name', required=True)
