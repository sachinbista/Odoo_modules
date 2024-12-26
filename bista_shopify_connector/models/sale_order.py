##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

import pprint
from .. import shopify
import logging
import time
import pytz
from datetime import datetime, timedelta
from dateutil import parser
import urllib.parse as urlparse
from odoo import fields, models, tools, _, api
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools.float_utils import float_round
from pyactiveresource.util import xml_to_dict
utc = pytz.utc

_logger = logging.getLogger("Shopify Order")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def update_order_status(self):
        """
          This method wwill check the pickings
          from the sale orders which are not updated
          at the shopify end at the fulfillment level.
          @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        for order in self:
            if order.shopify_config_id:
                pickings = order.picking_ids\
                    .filtered(lambda x: x.state != "cancel")
                if pickings:
                    outgoing_picking = pickings.filtered(
                        lambda x: x.location_dest_id.usage == "customer")
                    if all(outgoing_picking.mapped("is_updated_in_shopify")):
                        order.is_updated_in_shopify = True
                        continue
                order.is_updated_in_shopify = False
                continue
            order.is_updated_in_shopify = False

    shopify_order_id = fields.Char(string='Shopify Order ID', copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)
    shopify_order_name = fields.Char(
        string='Shopify Order', copy=False, help='Shopify Order Number')
    shopify_tag_ids = fields.Many2many(
        'shopify.tags', string='Shopify Tags', copy=False, help='Shopify Tags')
    is_updated_in_shopify = fields.Boolean(
        'Is Updated In Shopify', copy=False, readonly=True, default=False, compute='update_order_status')
    shopify_payment_gateway_id = fields.Many2one(
        'shopify.payment.gateway', string='Shopify Payment Gateway', copy=False)
    financial_workflow_id = fields.Many2one(
        'shopify.financial.workflow', copy=False)
    auto_workflow_id = fields.Many2one(
        'shopify.workflow.process', string='Auto Workflow', copy=False)
    shopify_cancelled_at = fields.Datetime(
        'Cancelled At', help="Order cancelled at in shopify", copy=False)
    cancel_reason = fields.Char(
        'Cancel Reason', help="Order cancel reason in shopify", copy=False)
    downpayment_history_ids = fields.One2many(
        'sale.downpayment.history', 'sale_id', string="Downpayment History", copy=False)
    remaining_downpayment = fields.Float(string="Remaining Downpayment",
                                         compute="get_remaining_downpayment",
                                         store=True)
    is_unearned_revenue_order = fields.Boolean('Is Unearned Revenue Order',
                                               copy=False, readonly=True)
    is_risk_order = fields.Boolean('Is Risk Order', copy=False)
    shop_risk_ids = fields.One2many("shopify.risk.order", 'order_id', "Risks Order",
                                    copy=False)
    has_rounding_diff = fields.Boolean('Has Rounding Diff', copy=False)
    shopify_financial_status = fields.Char('Financial Status')
    shopify_fulfillment_status = fields.Char('Fulfillment Status')
    is_manual_shopify_payment = fields.Boolean(
        'Manual Shopify Payment', default=False)
    is_manual_odoo_refund = fields.Boolean(
        'Manual Odoo Refund To Shopify', default=False)

    @api.depends('downpayment_history_ids', 'downpayment_history_ids.amount')
    def get_remaining_downpayment(self):
        """
            This method updated the amount of downpayment
            on its history according to remaining payments.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        for order in self:
            order.remaining_downpayment = sum(
                order.downpayment_history_ids.mapped('amount'))

    def manual_create_downpayment_invoice(self, movetype, amount):
        """
            This method creates the downpayment and reconciles accorindly.
            @return : created downpayment invoice.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        dpname = _('Down Payment')
        sale_adv_pay_inv_obj = self.env['sale.advance.payment.inv']
        dp_product_id = sale_adv_pay_inv_obj._compute_product_id()
        inv_vals = sale_adv_pay_inv_obj._prepare_invoice_values(
            order=self, name=dpname, amount=amount, so_line=self.env['sale.order.line'])
        inv_vals['invoice_line_ids'][0][2]['product_id'] = dp_product_id and dp_product_id.id or None
        if self.shopify_config_id.unearned_account_id:
            inv_vals['invoice_line_ids'][0][2]['account_id'] = self.shopify_config_id.unearned_account_id.id
        inv_vals['invoice_line_ids'][0][2]['sale_line_ids'] = False
        inv_vals.update({'move_type': movetype,
                         'sale_order_id': self.id,
                         'fiscal_position_id': self.fiscal_position_id.id})
        if movetype == 'out_invoice':
            inv_vals.update({'is_downpayment_inv': True})
        invoice = self.env['account.move'].sudo().create(inv_vals)
        invoice.action_post()
        self.env['sale.downpayment.history'].sudo().create(
            {
                'sale_id': self.id,
                'amount': invoice.amount_total_signed,
                'invoice_id': invoice.id})
        return invoice

    @api.depends('order_line.invoice_lines')
    def _get_invoiced(self):
        """
            Using this method linked the count of invoices which is as Shopify credeit and
            in odoo created as the invoice for refund order of Shopify note
            that is move_type has out_refund.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        super_data = super(SaleOrder, self)._get_invoiced()
        for order in self:
            refund_invoices = self.env['account.move'].sudo().search(
                [('move_type', '=', 'out_refund'),
                 ('sale_order_id', '=', order.id),
                 ('shopify_order_id', '=', order.shopify_order_id)])
            order.invoice_ids += refund_invoices
            order.invoice_count = len(order.invoice_ids)

    # link shopify credit note with order
    def action_view_invoice(self, invoices=False):
        """
            Using this method linked the count of credite notes which is as Shopify credit and
            in odoo created as the invoice for refund order of Shopify note.
            that is move_type has out_refund.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        super_data = super(SaleOrder, self).action_view_invoice(invoices)
        for sale in self:
            if sale.shopify_order_id:
                refund_invoices = self.env['account.move'].sudo().search(
                    [('move_type', '=', 'out_refund'),
                     ('sale_order_id', '=', sale.id),
                     ('shopify_order_id', '=', sale.shopify_order_id)])
                if refund_invoices:
                    action = self.env.ref(
                        'account.action_move_out_invoice_type').read()[0]
                    invoices = self.mapped('invoice_ids')
                    invoices += refund_invoices
                    action['domain'] = [('id', 'in', invoices.ids)]
                    context = {
                        'default_move_type': 'out_invoice',
                    }
                    if len(sale) == 1:
                        context.update({
                            'default_partner_id': sale.partner_id.id,
                            'default_partner_shipping_id': sale.partner_shipping_id.id,
                            'default_invoice_payment_term_id': sale.payment_term_id.id,
                            'default_invoice_origin': sale.mapped('name'),
                            'default_user_id': sale.user_id.id,
                        })
                    action['context'] = context
                    super_data = action
        return super_data

    def action_view_invoice_downpayment(self):
        """
            This method checks and map the down-payment
            invoices at the customer and order level.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        invoices = self.downpayment_history_ids.mapped('invoice_id')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        refund_invoices = self.env['account.move'].sudo().search(
            [('move_type', '=', 'out_refund'),
             ('sale_order_id', '=', self.id),
             ('shopify_order_id', '!=', False),
             ('is_downpayment_refund', '!=', False),
             ('shopify_order_id', '=', self.shopify_order_id)])
        if refund_invoices:
            invoices += refund_invoices
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + \
                    [(state, view)
                     for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action

    def action_confirm(self):
        """ sale order action_confirm method has been override"""
        res = super(SaleOrder, self).action_confirm()
        if self.picking_ids:
            [picking.write({'shopify_config_id': self.shopify_config_id.id,
                            'shopify_order_id': self.shopify_order_id,
                            }) for picking in self.picking_ids]
            for picking in self.picking_ids:
                picking.action_assign()
        return res

    def get_customer(self, shopify_customer_id, shopify_config, customer_data):
        """ This method returns existing shopify customer or creates new customer based on customer data in sales order """
        Partner = self.env['res.partner'].sudo()
        partner_id = Partner.search([('shopify_customer_id', '=', str(
            shopify_customer_id)), ('shopify_config_id', '=', shopify_config.id)], limit=1)
        if not partner_id:
            if shopify_config.is_create_customer:
                Partner.shopify_import_customer_by_ids(
                    shopify_config, shopify_customer_by_ids=shopify_customer_id, queue_line=self._context.get('queue_line_id'))
                # Partner.create_update_shopify_customers_temp(customer_data, shopify_config)
                partner_id = Partner.search([('shopify_customer_id', '=', str(
                    shopify_customer_id)), ('shopify_config_id', '=', shopify_config.id)], limit=1)
        return partner_id or False

    def get_product(self, shopify_variant_id, shopify_product_id, shopify_config, sku, barcode):
        """
            This method will search variant in shopify product product mapping and return odoo product from there.
            If variant id not found in shopify product product mapping, product API with ID will be called and
            new mapping will be created and then product will be returned from that new mapping.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        shopify_product_product_id = False
        shopifyProductTemplate = self.env['shopify.product.template']
        ShopifyProductProduct = self.env['shopify.product.product']
        odoo_product = shopifyProductTemplate.odoo_product_search_sync(
            shopify_config, sku, barcode)
        if odoo_product:
            ShopifyProductProduct = self.env['shopify.product.product']
            shopify_product_product_id = ShopifyProductProduct.sudo().search(
                [('product_variant_id', '=', odoo_product.id)], limit=1)
        else:
            if shopify_config.is_create_product:
                shopifyProductTemplate.shopify_import_product_by_ids(
                    shopify_config, shopify_product_by_ids=str(shopify_product_id))
                shopify_product_product_id = ShopifyProductProduct.search(
                    [('shopify_product_id', '=', shopify_variant_id)], limit=1)
        return shopify_product_product_id or False

    def get_shopify_custom_product(self, custom_product_name):
        """
            This method will search variant of custom product in shopify product product mapping and return odoo product from there.
            If variant id not found in shopify product product mapping, product API with ID will be called and
            new mapping will be created and then product will be returned from that new mapping.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        ShopifyProductMapping = self.env['shopify.product.mapping']
        ProductTemplateMapping = self.env['product.template']
        shopify_product_mapping_id = ShopifyProductMapping.sudo().search(
            [('shopiy_product_name', '=', custom_product_name)], limit=1)
        if shopify_product_mapping_id:
            return shopify_product_mapping_id.product_variant_id
        else:
            prod_tmpl_mapping_id = ProductTemplateMapping.sudo().search(
                [('name', '=', custom_product_name)], limit=1)
            if prod_tmpl_mapping_id:
                return prod_tmpl_mapping_id.product_variant_ids[0]
            else:
                return False

    def create_shipping_or_billing_address(self, vals, parent_id=False,
                                           atype=''):
        """
            This method creates shipping or billing addresses
            accosiated with particular customer of order on shopify.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        country_obj = self.env['res.country'].sudo()
        state_obj = self.env['res.country.state'].sudo()
        partner_obj = self.env['res.partner'].sudo()
        name = vals.get('name')
        phone = vals.get('phone')
        state_name = vals.get('province')
        state_code = vals.get('province_code')
        email = vals.get('email')
        parent_id = parent_id.id

        city = vals.get('city')
        zip = vals.get('zip')
        street = vals.get('address1')
        street1 = vals.get('address2')

        country_name = vals.get('country')
        country_code = vals.get('country_code')

        country = country_obj.search([('code', '=', country_code)])
        if not country:
            country = country_obj.search([('name', '=', country_name)])

        if not country:
            state = state_obj.search([('code', '=', state_code)])
        else:
            state = state_obj.search([('code', '=', state_code),
                                      ('country_id', '=', country.id)])

        if not state:
            if not country:
                state = state_obj.search([('name', '=', state_name)])
            else:
                state = state_obj.search([('name', '=', state_name),
                                          ('country_id', '=', country.id)])

        if len(state.ids) > 1:
            state = state_obj.search([('code', '=', state_code),
                                      ('name', '=', state_name)])

        address = self.env['res.partner'].sudo().search([
            ('name', '=', name), ('state_id', '=', state.id),
            ('city', '=', city), ('zip', '=', zip), ('street', '=', street),
            ('street2', '=', street1),
            ('parent_id', '=', parent_id),
            ('country_id', '=', country.id)], limit=1)
        if not address:
            address = self.env['res.partner'].sudo().create({
                'name': name, 'state_id': state.id, 'city': city, 'zip': zip,
                'street': street, 'street2': street1, 'country_id': country.id,
                'parent_id': parent_id, 'type': atype, 'email': email,
                'shopify_config_id': self.id,
                'phone': phone})
        return address

    def convert_date_utc(self, order_datetime=False):
        if order_datetime:
            date_order = parser.parse(order_datetime).astimezone(
                utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_order = str(time.strftime("%Y-%m-%d %H:%M:%S"))
        return date_order

    def get_financial_workflow(self, shopify_config, shopify_payment_gateway, shopify_financial_status, shopify_payment_term=False):
        """
            Serach and check for financial flow existance.
            @return : Financial workflow if found.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        financial_workflow_id = shopify_config.financial_workflow_ids.filtered(
            lambda r: r.payment_gateway_id.id == shopify_payment_gateway.id and r.financial_status == shopify_financial_status)

        return financial_workflow_id and financial_workflow_id[0] or False

    def fetch_gateway_from_transaction(self, shopify_order_id):
        """
            This method will fetch a gateway from the
            transactions and return it once fetch.
            @return : gateway
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        shopify_transactions = shopify.Transaction().find(
            order_id=str(shopify_order_id)
        )
        if shopify_transactions:
            for transaction in shopify_transactions:
                transaction_dict = transaction.to_dict()
                gateway = transaction_dict.get("gateway")
        else:
            gateway = "blank_gateway"
        return gateway

    def prepare_workflow_vals(self, order_dict, shopify_config):
        """
            If financial workflow doesn't exists then
            create with vals based on order's data.
            @return : Financial workflow vals for order.
            @author: Yogeshwar Chaudhari @Bista Solutions Pvt. Ltd.
        """
        gateway = self.fetch_gateway_from_transaction(order_dict.get('id'))
        shopify_payment_gateway_id = self.check_shopify_gateway(
            gateway, shopify_config)
        shopify_financial_status = order_dict.get('financial_status')
        if shopify_payment_gateway_id and shopify_financial_status:
            financial_workflow_id = self.get_financial_workflow(
                shopify_config, shopify_payment_gateway_id, shopify_financial_status)
            try:
                if not financial_workflow_id:
                    shopify_payment_getway = self.env['shopify.payment.gateway']
                    shopi_financial_wrkflow = self.env['shopify.financial.workflow']
                    payment_getway_id = shopify_payment_getway.search(
                        [('code', '=', gateway), ('shopify_config_id', '=', shopify_config.id)], limit=1)
                    if not payment_getway_id:
                        getway_vals = {
                            'name': gateway,
                            'code': gateway,
                            'shopify_config_id': shopify_config.id
                        }
                        payment_getway_id = shopify_payment_getway.create(
                            getway_vals)
                    shopify_workflow_process = self.env['shopify.workflow.process'].search([
                    ], limit=1)
                    account_payment_term = self.env['account.payment.term'].search(
                        [('name', '=', 'Immediate Payment')])
                    financial_wrkflow_vals = {'shopify_config_id': shopify_config.id,
                                              'company_id': shopify_config.default_company_id.id,
                                              'auto_workflow_id': shopify_workflow_process.id,
                                              'payment_term_id': account_payment_term.id,
                                              'financial_status': shopify_financial_status,
                                              'payment_gateway_id': payment_getway_id.id,
                                              }
                    financial_workflow_id = shopi_financial_wrkflow.create(
                        financial_wrkflow_vals)
                    return {'financial_workflow_id': financial_workflow_id.id,
                            'shopify_payment_gateway_id': shopify_payment_gateway_id.id,
                            'auto_workflow_id': financial_workflow_id.auto_workflow_id.id,
                            'payment_term_id': financial_workflow_id.payment_term_id.id
                            }
                return {'financial_workflow_id': financial_workflow_id.id,
                        'shopify_payment_gateway_id': shopify_payment_gateway_id.id,
                        'auto_workflow_id': financial_workflow_id.auto_workflow_id.id,
                        'payment_term_id': financial_workflow_id.payment_term_id.id
                        }
            except Exception as e:
                raise UserError(_("Workflow not found. Configure workflow with Shopify Payment gateway '%s' and Financial Status '%s'." % (
                    gateway, shopify_financial_status)))

    def prepare_order_vals(self, partner_id, billing_addr_id, shipping_addr_id, order_dict, shopify_config):
        """
            This method is to prepare the order values
            from the dicstionary that is fetched from shopify.
            @return : Order values for creation.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        shopify_order_id = order_dict.get('id')
        shopify_order_name = order_dict.get('name')
        shopify_note = order_dict.get('note')
        shopify_order_date = order_dict.get('created_at')
        order_date = self.convert_date_utc(shopify_order_date)
        shopify_tags = order_dict.get('tags')
        shopify_financial_status = order_dict.get('financial_status')
        fulfillment_status = order_dict.get('fulfillment_status')
        source = order_dict.get('source_name')
        order_vals = {'partner_id': partner_id.id,
                      'partner_invoice_id': billing_addr_id.id,
                      'partner_shipping_id': shipping_addr_id.id,
                      'shopify_order_id': shopify_order_id,
                      'shopify_order_name': shopify_order_name,
                      'shopify_config_id': shopify_config.id,
                      'note': shopify_note,
                      'date_order': order_date,
                      'warehouse_id': shopify_config.warehouse_id.id,
                      'payment_term_id': shopify_config.default_payment_term_id.id,
                      'company_id': shopify_config.default_company_id.id,
                      'pricelist_id': shopify_config.pricelist_id.id or partner_id.property_product_pricelist.id,
                      'shopify_financial_status': shopify_financial_status,
                      'shopify_fulfillment_status': fulfillment_status,
                      }
        if shopify_tags:
            tag_ids = self.create_shopify_order_tags_in_odoo(shopify_tags)
            if tag_ids:
                order_vals.update({'shopify_tag_ids': [(6, 0, tag_ids.ids)]})
        return order_vals

    def create_shopify_order_tags_in_odoo(self, shopify_tags):
        """
            This method is creating the shopify order tags
            in odoo as a new object records,
            @return : tag records that is created.
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        shopify_tags_obj = self.env['shopify.tags']
        tag_list = list(shopify_tags.split(","))
        list_tags = []
        for tag in tag_list:
            updated_tag = tag.strip()
            tag_id = shopify_tags_obj.search([('name', '=', updated_tag)])
            if not tag_id:
                tag_id = shopify_tags_obj.create({'name': tag})
            list_tags.append(tag_id.id)
        tag_ids = shopify_tags_obj.browse(list_tags)
        return tag_ids

    def shopify_create_tax(self, tax_line, taxes_included, shopify_config):
        """
            This method is creating the shopify taxes from
            orders in odoo if not exists.
            @return : Tax_id that is created.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        Tax = self.env['account.tax'].sudo()
        rate = float(tax_line.get('rate', 0.0)) * 100
        title = tax_line.get("title")
        rate_calc = round(rate, 4)
        name = "%s%s%s" % (title, rate_calc, '%')
        tax_id = Tax.create({'name': name,
                             'description': name,
                             'amount': rate_calc,
                             'type_tax_use': 'sale',
                             'price_include': taxes_included,
                             'company_id': shopify_config.default_company_id.id,
                             'active': True})
        tax_id.mapped("invoice_repartition_line_ids").write(
            {"account_id": shopify_config.default_tax_account_id and shopify_config.default_tax_account_id.id or False})
        tax_id.mapped("refund_repartition_line_ids").write(
            {"account_id": shopify_config.default_tax_cn_account_id.id and shopify_config.default_tax_cn_account_id.id or False})
        return tax_id

    def get_tax_ids(self, shopify_tax_lines, taxes_included, shopify_config):
        """
            This method is fetching taxes from
            orders in odoo if not exists it creates new.
            @return : Taxes
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        taxes = []
        for line in shopify_tax_lines:
            if line and line.get('rate') in [0.0, 0.00]:
                title = line.get('title')
                price = float(line.get('price'))
                price_calc = round(price, 4)
                name = "%s%s%s" % (title, price_calc, '%')
                if price != 0.0:
                    tax_id = self.env["account.tax"].search([('price_include', '=', taxes_included),
                                                            ('amount', '=', price_calc),
                                                            ('type_tax_use', '=', 'sale'),
                                                            ('company_id', '=', shopify_config.default_company_id.id),
                                                            ('name', '=', name),
                                                            ('active','=',True)], limit=1)
                    if not tax_id:
                        tax_id = self.shopify_create_tax(
                            line, taxes_included, shopify_config)
                    if tax_id:
                        taxes.append(tax_id.id)
            else:
                rate = float(line.get('rate', 0.0)) * 100
                title = line.get('title')
                price = float(line.get('price'))
                rate_calc = round(rate, 4)
                name = "%s%s%s" % (title, rate_calc, '%')
                if price != 0.0:
                    tax_id = self.env["account.tax"].search([('price_include', '=', taxes_included),
                                                             ('amount', '=',
                                                              rate_calc),
                                                             ('type_tax_use',
                                                              '=', 'sale'),
                                                             ('company_id', '=',
                                                              shopify_config.default_company_id.id),
                                                             ('name', '=', name),
                                                             ('active', '=', True)], limit=1)
                    if not tax_id:
                        tax_id = self.shopify_create_tax(
                            line, taxes_included, shopify_config)
                    if tax_id:
                        taxes.append(tax_id.id)
        return taxes

    def shopify_import_orders_by_webhook(self,order_dict ,shopify_config):
        """This method is used to create queue and queue line for orders that came by webhook"""
        shopify_config.check_connection()
        if order_dict:
            payment_gateway = []
            shop_queue_id = shopify_config.action_create_queue(
                'import_order',True)
            name = order_dict.get('name', '')
            line_vals = {
                'shopify_id': order_dict.get('id') or '',
                'state': 'draft',
                'name': name and name.strip(),
                'record_data': pprint.pformat(order_dict),
                'shopify_config_id': shopify_config.id,
            }
            shop_queue_id.action_create_queue_lines(line_vals)
            gateway = self.fetch_gateway_from_transaction(order_dict.get('id'))
            payment_gateway.append(gateway)
            # Code for checking shopify payment gateway and create if does not exist
            for gateway in list(set(payment_gateway)):
                if not self.check_shopify_gateway(gateway, shopify_config):
                    self.create_shopify_payment_gateway(
                        gateway, shopify_config)
            # shopify_config.sudo().write({'last_import_order_date':fields.Datetime.now()})
        return True

    def get_carrier(self, code, title, shopify_config):
        """
            This method is fetching carrier from shopify
            orders in odoo if not exists it creates new.
            @return : Carrier
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        DeliveryCarrier = self.env['delivery.carrier']
        shipping_product_id = shopify_config.shipping_product_id
        carrier_id = DeliveryCarrier.search(
            [('code', '=', code), ('name', '=', title)], limit=1)
        if not carrier_id:
            carrier_id = DeliveryCarrier.sudo().create({'code': code,
                                                        'name': title,
                                                        'product_id': shipping_product_id.id,
                                                        })
        return carrier_id

    def check_carrier(self, name, service):
        """
            Return carrier information based on carrier name in case not
            found Odoo will create new based on name.
            @return : carrier_id
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        if name:
            carrier_obj = self.env['delivery.carrier']
            domain = [('name', '=', name)]
            # if service: #TODO: Check for service when delivery carrier is FedEx, USPS etc
            #     domain += [('delivery_type', '=', service)]
            carrier_id = carrier_obj.search(domain, limit=1)
            if not carrier_id:
                product_id = self.env.ref(
                    'bista_shopify_connector.shopify_shipping_product')
                carrier_id = carrier_obj.sudo().create({'name': name,
                                                        'product_id': product_id.id})
            return carrier_id

    def prepare_order_line_vals(self, shopify_line, product_id, taxes_included, shopify_config, shopify_line_id):
        """
            This method prepares the order line
            related values from order dict coming from shopify.
            @return : order_lines,tax_ids
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
         """
        shopify_variant_id = shopify_line.get('variant_id')
        shopify_product_id = shopify_line.get('product_id')
        qty = shopify_line.get('quantity')
        price_unit = shopify_line.get('price') and float(shopify_line['price'])
        shopify_tax_lines = shopify_line['tax_lines']
        discount_lines = shopify_line.get('discount_allocations', False)
        # shopify_product_product_id = self.get_product(shopify_variant_id, shopify_product_id, shopify_config)
        # product_id = shopify_product_product_id.product_variant_id
        product_product_obj = self.env['product.product'].search(
            [('id', '=', product_id.id)])
        sproduct_obj = self.env['shopify.product.product'].search(
            [('id', '=', product_id.id)])
        if product_product_obj:
            product_uom = product_product_obj.product_tmpl_id.uom_id.id or False
            if product_product_obj.default_code:
                product_name = '[' + product_product_obj.default_code + ']' + \
                    product_product_obj.product_tmpl_id.name
            else:
                product_name = product_product_obj.product_tmpl_id.name
        else:
            if sproduct_obj:
                product_uom = sproduct_obj.product_template_id.uom_id.id or False
                if sproduct_obj.product_variant_id.default_code:
                    product_name = '[' + sproduct_obj.product_variant_id.default_code + ']' + \
                        sproduct_obj.product_template_id.name
                else:
                    product_name = sproduct_obj.product_template_id.name
        order_line_dict = {
            'shopify_line_id': shopify_line_id,
            'shopify_config_id': shopify_config.id,
            'name': product_name,
            'product_id': product_id.id,
            'product_uom_qty': qty,
            'product_uom': product_uom,
            'price_unit': price_unit,
            'shopify_price_unit': price_unit,
        }
        # TODO: Tax based on fiscal position defined in odoo
        tax_ids = self.get_tax_ids(
            shopify_tax_lines, taxes_included, shopify_config)
        # if tax_ids:
        order_line_dict.update({'tax_id': [(6, 0, tax_ids)]})
        if discount_lines:
            discount_amount_total = self.get_discount_amount(discount_lines)
            price_unit -= (discount_amount_total / qty)
            if price_unit < 0.0:
                price_unit = 0.0
            order_line_dict.update({
                # 'price_unit': price_unit,
                'shopify_discount_amount': discount_amount_total
            })
            # order_line_dict['price_unit'] = price_unit
        return order_line_dict, tax_ids

    def get_discount_amount(self, discount_lines):
        """
           This method updates the discount amounts
           from order dict coming from shopify.
           @return : discount_amount
           @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
       """
        discount_amount = 0.0
        for discount_line in discount_lines:
            discount_amount += float(discount_line.get('amount', 0.0))
        return discount_amount

    def prepare_discount_line_vals(self, product_id, discount_lines, tax_ids, shopify_config):
        """
            This method prepares the discount lines
            from order dict coming from shopify.
            @return : discount_line_dict
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        discount_product_id = shopify_config.disc_product_id
        if not discount_product_id:
            raise UserError(_("Discount Product not configured."))
        discount_amount = 0.0
        # discount_lines = line.get('discount_allocations')
        for discount_line in discount_lines:
            discount_amount += float(discount_line.get('amount', 0.0))
        name = "Discount for product %s" % product_id.name
        discount_line_dict = {}
        if discount_amount > 0:
            discount_line_dict = {'name': name,
                                  'product_id': discount_product_id.id,
                                  'product_uom_qty': 1,
                                  'product_uom': discount_product_id.uom_id and discount_product_id.uom_id.id or False,
                                  'price_unit': discount_amount * -1,
                                  'tax_id': tax_ids,
                                  }
        return discount_line_dict

    def check_rounding_diff(self, order_id, shopify_total_amount, shop_error_log_id, queue_line_id):
        """
        This method will check rounding diff of odoo order total amount and shopify total amount.
        If rounding diff in [-0.01,-0.02,0.01,0.02] then add sale order line and create error log
        If rounding diff not in about list, then import order and create error log
        """
        error_log_env = self.env['shopify.error.log'].sudo()
        precision_price = self.env['decimal.precision'].precision_get(
            'Product Price')
        product_id = self.env.ref(
            'bista_shopify_connector.shopify_rounding_diff_product')
        order_total_amount = order_id.amount_total
        diff = float_round(
            (order_total_amount - shopify_total_amount), precision_digits=precision_price)
        SaleOrderLine = self.env['sale.order.line']
        rounding_diff_desc = "Shopify Order rounding difference"
        if diff != 0:
            if not product_id:
                raise UserError(_("Rounding Difference product not found"))
            if diff in [-0.01, -0.02, -0.03, -0.04, -0.05, 0.01, 0.02, 0.03, 0.04, 0.05]:
                line_vals_dict = {
                    'product_id': product_id.id,
                    'name': rounding_diff_desc,
                    'price_unit': abs(diff),
                    'product_uom_qty': diff > 0 and -1 or 1,
                    'product_uom': product_id.uom_id.id,
                    'order_id': order_id.id
                }
                order_line_id = SaleOrderLine.create(line_vals_dict)
            order_id.has_rounding_diff = True
            error_log_env.sudo().create_update_log(
                shop_error_log_id=shop_error_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': "Order %s has rounding diff" % order_id.shopify_order_id,
                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

    def calculate_discount_amount(self, amount, price):
        """
            Calculate the discount percentage based on amount
            and returns the percentage.
            return : discount_percentage
            author : Nupur Soni @Bista Solutions
        """
        discount_amount = float(amount)
        unit_price = float(price)
        discount_percentage = (discount_amount * 100) / unit_price
        return discount_percentage

    def prepare_shipping_line_vals(self, shipping_line, taxes_included, shopify_config):
        """
            This method prepares the shipping lines
            from order dict coming from shopify.
            @return : shipping_line_dict
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        shipping_product_id = shopify_config.shipping_product_id
        if not shipping_product_id:
            raise UserError(_("Discount Product not configured."))
        shipping_price = float(shipping_line.get('price', 0.0))
        shipping_line_dict = {'name': shipping_product_id.name,
                              'product_id': shipping_product_id.id,
                              'product_uom_qty': 1,
                              'product_uom': shipping_product_id.uom_id and shipping_product_id.uom_id.id or False,
                              'price_unit': shipping_price,
                              }
        shipping_tax_lines = shipping_line.get('tax_lines')
        tax_ids = self.get_tax_ids(
            shipping_tax_lines, taxes_included, shopify_config)
        if tax_ids:
            shipping_line_dict.update({'tax_id': [(6, 0, tax_ids)]})
        return shipping_line_dict

    def get_shopify_location(self, shopify_location_id, shopify_config):
        """
            This method fetch location details from the shopify
            fulfilled orders, mapped based on location_id at odoo end.
            @return : location_id
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        location_id = self.env['stock.location'].sudo().search([('shopify_location_id', '=', shopify_location_id),
                                                                ('shopify_config_id',
                                                                 '=', shopify_config.id),
                                                                ('usage', '=',
                                                                 'internal')
                                                                ], limit=1)
        return location_id.id or False
        # warehouse_id = self.env['stock.warehouse'].search([('shopify_warehouse_id', '=', shopify_location_id)])
        # picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'),
        #                                                          ('warehouse_id.shopify_warehouse_id', '=', shopify_location_id),
        #                                                          ('warehouse_id.shopify_config_id', '=', shopify_config.id)
        #                                                          ], limit=1)
        # return picking_type_id.id or False

    def get_shopify_warehouse_location(self, order_dict, shopify_config):
        """
            This method fetch location details from the shopify
            fulfilled orders, mapped based on location_id at odoo end.
            @return : location_id,warehouse_id
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        shopify_location_id = False
        if order_dict.get('location_id'):
            shopify_location_id = order_dict.get('location_id')
        elif order_dict.get("fulfillments"):
            shopify_location_id = order_dict.get(
                "fulfillments")[0].get('location_id')

        location_id = self.env['stock.location'].sudo().search([('shopify_location_id', '=', shopify_location_id),
                                                                ('shopify_config_id',
                                                                 '=', shopify_config.id),
                                                                ('usage', '=', 'internal')], limit=1)
        warehouse_id = self.env['stock.warehouse'].search(
            [('shopify_config_id', '=', shopify_config.id)], limit=1)
        if not warehouse_id:
            warehouse_id = shopify_config.warehouse_id
            # raise UserError(_("Shopify Location with id %s not found." % shopify_location_id))
        return {'location_id': location_id or False, 'warehouse_id': warehouse_id}

    # def process_picking(self, picking_id, fulfilment_line, shopify_config):
    #     """
    #         Using this method processing the picking.
    #     """
    #     # Avoid updating inv in shopify at the time of import order and process DO
    #     shopify_product_obj = self.env['shopify.product.product']
    #     product_product_obj = self.env['product.product']
    #     for item_line in fulfilment_line.get('line_items'):
    #         shopify_product_id = item_line.get(
    #             'product_id') and str(item_line.get('product_id'))
    #         qty_done = item_line.get('quantity')
    #         product_id = False
    #         sku = item_line.get('sku')
    #         barcode = item_line.get('barcode')
    #         if item_line.get('variant_id') and item_line.get('product_id'):
    #             shopify_product_product_id = self.get_product(item_line.get(
    #                 'variant_id'), item_line.get('product_id'), shopify_config, sku, barcode)
    #             product_id = shopify_product_product_id or shopify_product_product_id.product_variant_id or False
    #         else:
    #             # For custom product
    #             shopify_custom_product_name = item_line.get(
    #                 'name') and item_line.get('name').strip()
    #             product_id = self.get_shopify_custom_product(
    #                 shopify_custom_product_name)
    #         product_id = product_product_obj.search(
    #             [('id', '=', product_id.id)])
    #         if product_id:
    #             if product_id and product_id.product_tmpl_id.type == 'service':
    #                 return False
    #         else:
    #             shopify_product_id = shopify_product_obj.search(
    #                 [('id', '=', product_id.id)])
    #             if shopify_product_id and shopify_product_id.product_template_id.type == 'service':
    #                 return False
    #         if not product_id:
    #             raise (_("Product '%s' not found" % item_line.get('name')))
    #         move_ids = picking_id.move_ids_without_package.filtered(lambda r: r.product_id.id == product_id.id)
    #         picking_id.action_assign()
    #         for move in move_ids:
    #             update_qty = 0.00
    #             if move.availability and qty_done <= move.availability :
    #                 update_qty = qty_done
    #             elif move.availability > 0:
    #                 update_qty = move.availability
    #             if update_qty > 0:
    #                 move.quantity = update_qty
    #                 if qty_done > move.availability:
    #                     raise UserError(_("Please update quantity of '%s' on '%s' to process the order '%s'!") %
    #                     (product_id.name, picking_id.location_id.complete_name,picking_id.sale_id.name))
    #             else:
    #                 raise UserError(_("Please update quantity of '%s' on '%s' to process the order '%s'!") %
    #                     (product_id.name, picking_id.location_id.complete_name,picking_id.sale_id.name))
    #     carrier_id = self.check_carrier(fulfilment_line.get(
    #         'tracking_company'), fulfilment_line.get('service'))
    #     picking_id.carrier_id = carrier_id and carrier_id.id or None
    #     picking_id.action_assign()
    #     picking_validate = picking_id.with_context(
    #         skip_sms=True, shopify_picking_validate=True).button_validate()
    #     if isinstance(picking_validate, dict):
    #         if picking_validate.get('res_model') == 'stock.backorder.confirmation':
    #             ctx = picking_validate.get('context')
    #             backorder_id = self.env['stock.backorder.confirmation'].with_context(
    #                 ctx).create({'pick_ids': [(4, picking_id.id)]})
    #             backorder_id.process()
    #     picking_id.write({'shopify_fulfillment_id': fulfilment_line.get('id') and str(fulfilment_line.get('id')) or None,
    #                       'shopify_order_id': self._context.get('shopify_order_id', None),
    #                       'shopify_fulfillment_service': fulfilment_line.get('service'),
    #                       'shopify_config_id': shopify_config.id,
    #                       'carrier_tracking_ref': fulfilment_line.get('tracking_number'),
    #                       'is_updated_in_shopify': True,
    #                       })

    def process_picking(self, picking_id, fulfilment_line, shopify_config):
        """
            This method fetch location details from the shopify
            fulfilled orders, and process the odoo delivery order according
            to the shopify if order at shopify is fulfilled then it will process
            delivery order as done.If order is parial fulfilled then it will
            create a back order in odoo.
            @return : location_id,warehouse_id
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
         """
        for item_line in fulfilment_line.get('line_items'):
            shopify_product_id = item_line.get(
                'product_id') and str(item_line.get('product_id'))
            qty_done = item_line.get('quantity')
            product_id = False
            sku = item_line.get('sku')
            barcode = item_line.get('barcode')
            if item_line.get('variant_id') and item_line.get('product_id'):
                shopify_product_product_id = self.get_product(item_line.get(
                    'variant_id'), item_line.get('product_id'), shopify_config, sku, barcode)
                product_id = shopify_product_product_id.product_variant_id or False
            else:
                # For custom product
                shopify_custom_product_name = item_line.get(
                    'name') and item_line.get('name').strip()
                product_id = self.get_shopify_custom_product(
                    shopify_custom_product_name)
            if product_id and product_id.type == 'service':
                return False
            if not product_id:
                raise (_("Product '%s' not found" % item_line.get('name')))
            sale_line_id = item_line.get('id')
            move_ids = picking_id.move_ids_without_package.filtered(
                lambda r: r.product_id.id == product_id.id)
            picking_id.action_assign()
            for move in move_ids:
                if move.sale_line_id.shopify_line_id == str(sale_line_id):
                    update_qty = 0.00
                    if move.availability and qty_done <= move.availability:
                        update_qty = qty_done
                    elif move.availability > 0:
                        update_qty = move.availability
                    if update_qty > 0:
                        move.quantity = update_qty
                        if qty_done > move.availability:
                            raise UserError(
                                _("Please update quantity of '%s' on '%s' to process the order '%s'!") %
                                (product_id.name, picking_id.location_id.complete_name, picking_id.sale_id.name))
                    else:
                        raise UserError(
                            _("Please update quantity of '%s' on '%s' to process the order '%s'!") %
                            (product_id.name, picking_id.location_id.complete_name, picking_id.sale_id.name))
        carrier_id = self.check_carrier(fulfilment_line.get(
            'tracking_company'), fulfilment_line.get('service'))
        picking_id.carrier_id = carrier_id and carrier_id.id or None
        picking_id.action_assign()
        picking_validate = picking_id.with_context(
            skip_sms=True, shopify_picking_validate=True).button_validate()
        if isinstance(picking_validate, dict):
            if picking_validate.get(
                    'res_model') == 'stock.backorder.confirmation':
                ctx = picking_validate.get('context')
                backorder_id = self.env['stock.backorder.confirmation'].with_context(
                    ctx).create({'pick_ids': [(4, picking_id.id)]})
                backorder_id.process()
        picking_id.write(
            {
                'shopify_fulfillment_id': fulfilment_line.get('id') and str(
                    fulfilment_line.get('id')) or None,
                'shopify_order_id': self._context.get(
                    'shopify_order_id',
                    None),
                'shopify_fulfillment_service': fulfilment_line.get('service'),
                'shopify_config_id': shopify_config.id,
                'carrier_tracking_ref': fulfilment_line.get('tracking_number'),
                'is_updated_in_shopify': True,
            })

    def process_fullfilled_orders(self, shopify_fulfilment_lines, shopify_config):
        """
            This method is process the fullfilled orders from shopify.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        for line in shopify_fulfilment_lines:
            if line.get('status') == 'success':
                fulfilled_picking_id = self.picking_ids.filtered(
                    lambda r: r.shopify_fulfillment_id == str(line.get('id')))
                if fulfilled_picking_id:
                    continue
                shopify_location_id = line.get(
                    'location_id') and str(line.get('location_id'))
                create_dt = line.get('created_at')
                picking_id = self.picking_ids.filtered(lambda r: r.state not in [
                    'cancel', 'done'] and r.location_id.shopify_location_id == shopify_location_id)
                if picking_id:
                    self.process_picking(picking_id, line, shopify_config)
                else:
                    picking_id = self.picking_ids.filtered(
                        lambda r: r.state not in ['cancel', 'done'] and not r.shopify_fulfillment_id)
                    if picking_id:
                        # TODO: Fix for updating operation type in picking for correct location
                        picking_id.location_id = self.get_shopify_location(
                            shopify_location_id, shopify_config)
                        self.process_picking(picking_id, line, shopify_config)
                # if self._context.get('create_invoice', False) and self.invoice_status == 'to invoice':
                #     self.create_shopify_invoice(shopify_config)
                    # TODO: FIX it. Line data not getting proper i.e. getting str instead of dict
                    # self.process_fullfilled_orders(line, shopify_config)

    def fetch_order_fulfillment_location_from_shopify(self, shopify_order_dict):
        """
        This method set location in the Shopify order line dict.
        """
        fulfillments = shopify.FulfillmentOrders.find(
            order_id=shopify_order_dict.get('id'))
        fulfillment_list = [fulfillment.to_dict()
                            for fulfillment in fulfillments]
        if fulfillment_list:
            for fulfillment_dict in fulfillment_list:
                for line_item in fulfillment_dict.get('line_items'):
                    [shopify_order_line_item.update({'location_id': fulfillment_dict.get('assigned_location_id')}) for shopify_order_line_item in shopify_order_dict.get('line_items', []) if
                     shopify_order_line_item.get('id') == line_item.get('line_item_id')]
        return shopify_order_dict

    def process_shopify_order_fullfillment(self, shopify_config, fulfillment_status=False, fulfillment_lines=[]):
        """
            Check state of order and confirm it to create delivery order if required.
            Process delivery order in odoo based on fulfilment data received.
            @author: Yogeshwar Chaudhari @Bista Solutions Pvt. Ltd.
        """
        if self.state not in ["sale", "done", "cancel"]:
            self.action_confirm()
        if fulfillment_status in ['partial', 'fulfilled'] and fulfillment_lines:
            self.process_fullfilled_orders(fulfillment_lines, shopify_config)
        # elif fulfillment_status == 'partial' and fulfillment_lines:
        #     self.process_fullfilled_orders(fulfillment_lines, shopify_config)
        # TODO: Method call for processing delivery order

    def prepare_return_picking_vals(self, shopify_config, order_id, picking_id, shopify_refund_id):
        """
            This method is prepares the return picking
            values and returnit for creation.
            @return : picking_vals
            @autthor : Ashwin Khodifad
        """
        picking_type_id = picking_id.picking_type_id.return_picking_type_id
        location_dest_id = self.env['stock.location'].sudo().search([('is_shopify_return_location', '=', True),
                                                                     ('shopify_config_id', '=', shopify_config.id)], limit=1)
        if not location_dest_id:
            location_dest_id = picking_id.location_id
        if not picking_type_id:
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'),
                                                                     ('warehouse_id', '=',
                                                                      order_id.warehouse_id.id),
                                                                     ('company_id', '=', order_id.company_id.id)], limit=1)
        partner_id = order_id.partner_id
        if order_id.picking_ids:
            delivery_id = order_id.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing')
            partner_id = delivery_id and delivery_id[0].partner_id
        vals = {
            'partner_id': partner_id.id,
            'picking_type_id': picking_type_id.id,
            'origin': order_id.name,
            'group_id': picking_id.group_id.id,
            'company_id': picking_id.company_id.id,
            'shopify_order_id': picking_id.shopify_order_id,
            'shopify_refund_id': shopify_refund_id,
            'location_dest_id': location_dest_id.id,
            'location_id': picking_id.location_dest_id.id,
            'picking_return_id': picking_id.id,
        }
        return vals

    def create_return_picking_move(self, refund_line, return_picking_id, procurement_group_id):
        """
            This method will create a picking for return.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        StockMove = self.env['stock.move']
        qty = refund_line.get('quantity')
        line_item_id = refund_line.get('line_item_id')
        order_line_id = self.env['sale.order.line'].search(
            [('shopify_line_id', '=', line_item_id)], limit=1)
        if order_line_id:
            product_id = order_line_id.product_id
            vals = {
                'name': '/',
                'product_id': product_id.id,
                'product_uom': product_id.uom_id.id,
                'product_uom_qty': qty,
                'quantity': qty,
                'location_id': return_picking_id.location_id.id,
                'location_dest_id': return_picking_id.location_dest_id.id,
                'to_refund': True,
                'group_id': procurement_group_id.id,
                'picking_id': return_picking_id.id,
                'sale_line_id': order_line_id.id,
                # As this parameter is used in base module we have added it. If requird, we can remove it in future
                'procure_method': 'make_to_stock',
            }
            move_id = StockMove.create(vals)
            move_id._onchange_product_id()
            move_id.update({'state': 'assigned'})
        else:
            raise UserError(
                _("Order Line not found for shopify line id %s." % line_item_id))

    def create_return_pickings(self, shopify_config, order_id, refund_data):
        """
            This method will create a picking for return.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        StockPicking = self.env['stock.picking']
        if not self.is_manual_shopify_payment and not self.is_manual_odoo_refund:
            for refund_line in refund_data:
                picking_ids = order_id.picking_ids.filtered(
                    lambda l: l.picking_type_id.code == 'outgoing')
                picking_id = (picking_ids and picking_ids[0]) or (
                    self.picking_ids and self.picking_ids[0])
                if picking_id:
                    if refund_line.get('restock'):
                        shopify_refund_id = str(refund_line.get('id'))
                        return_picking_id = order_id.picking_ids.filtered(
                            lambda r: r.picking_type_id.code == 'incoming' and r.shopify_refund_id == shopify_refund_id)
                        if return_picking_id:
                            continue
                        return_picking_vals = self.prepare_return_picking_vals(
                            shopify_config, order_id, picking_id, shopify_refund_id)
                        refund_line_items = refund_line.get(
                            'refund_line_items')
                        return_move_ids = []
                        new_return_picking_id = StockPicking
                        for line in refund_line_items:
                            # TODO: Check for return reason to be stored at picking level
                            # don't added picking line if product type is service
                            line_item_id = line.get('line_item_id')
                            line_item_quantity = line.get('quantity')
                            order_line_id = self.env['sale.order.line'].search(
                                [('shopify_line_id', '=', line_item_id)], limit=1)
                            if (line.get('restock_type') != 'return') or (order_line_id and order_line_id.product_id.type == 'service'):
                                # if line.get('restock_type') == 'cancel':
                                #     product_uom_qty = order_line_id.product_uom_qty - line_item_quantity
                                #     order_line_id.update({'product_uom_qty': product_uom_qty})
                                #     picking_id.action_cancel()
                                continue
                            if not new_return_picking_id:
                                new_return_picking_id |= StockPicking.create(
                                    return_picking_vals)
                            self.create_return_picking_move(
                                line, new_return_picking_id, picking_id.group_id)
                        if new_return_picking_id:
                            new_return_picking_id.action_confirm()
                            new_return_picking_id.with_context(
                                skip_sms=True, shopify_picking_validate=True).button_validate()
        else:
            pass

    def create_shopify_credit_note_in_odoo(self, invoice_id):
        """
            This method will use to create shopify order credit note for fully invoice.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        if self.is_manual_shopify_payment is False and self.is_manual_odoo_refund is False:
            invoice = invoice_id.filtered(
                lambda l: l.state != 'cancel' and not l.is_downpayment_inv and l.move_type == 'out_invoice')
            if self.downpayment_history_ids:
                invoice_id = self.downpayment_history_ids.mapped('invoice_id')
                invoice = invoice_id.filtered(
                    lambda l: l.state != 'cancel' and l.move_type == 'out_invoice')
            if not invoice:
                return False
            shopify_transactions = shopify.Transaction().find(
                order_id=str(self.shopify_order_id))
            for transaction in shopify_transactions:
                transaction_dict = transaction.to_dict()
                transaction_id = transaction_dict.get('transaction', {}).get(
                    'id') or transaction_dict.get('id')
                transaction_type = transaction_dict.get('transaction', {}).get(
                    'kind') or transaction_dict.get('kind')
                status = transaction_dict.get('transaction', {}).get(
                    'status') or transaction_dict.get('status')
                # if transactions are completed create payment else continue
                if transaction_type not in ['refund'] or status != 'success':
                    continue
                if invoice_id:
                    refund_invoice = self.env['account.move'].sudo().search([
                        ('state', '!=', 'cancel'),
                        ('shopify_order_id', '=', self.shopify_order_id),
                        ('shopify_config_id', '=', self.shopify_config_id.id),
                        ('shopify_transaction_id', '=', str(transaction_id)),
                        ('sale_order_id', '=', self.id),
                        ('move_type', '=', 'out_refund')])
                    if not refund_invoice:
                        amount = transaction_dict.get('transaction', {}).get(
                            'amount') or transaction_dict.get('amount')
                        msg = transaction_dict.get('message')
                        refund_journal_id = self.auto_workflow_id.credit_note_journal_id
                        if self.amount_total == float(amount):
                            # if ful refund create down-payment invoice reversal create note else create direct create note
                            move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move",
                                                                                           active_ids=(invoice[0].ids)).create(
                                {'reason': "Shopify Refund", 'refund_method': 'refund',
                                    'date': self.date_order or fields.Datetime.now(),
                                 'journal_id': refund_journal_id and refund_journal_id.id or invoice[0].journal_id.id, })
                            reversal = move_reversal.reverse_moves()
                            refund_invoice = self.env['account.move'].sudo().browse(
                                reversal['res_id'])
                        # if amount not equal to order than create credit note based on transaction amount.
                        else:
                            refund_journal_id = self.auto_workflow_id.credit_note_journal_id
                            unearned_account_id = False
                            if self.downpayment_history_ids:
                                unearned_account_id = self.shopify_config_id.unearned_account_id.id
                            vals = {
                                'shopify_config_id': self.shopify_config_id.id,
                                'invoice_date': self.date_order,
                                'ref': 'Reversal of: %s' % self.shopify_order_name,
                                'partner_id': self.partner_id.id,
                                'journal_id': refund_journal_id.id,
                                'currency_id': self.currency_id.id,
                                'move_type': 'out_refund',
                                'shopify_order_id': self.shopify_order_id,
                                'sale_order_id': self.id,
                                'invoice_origin': self.shopify_order_name or '',
                                'shopify_transaction_id': str(transaction_id),
                                'invoice_line_ids': [(0, 0, {
                                    'name': msg,
                                    'account_id': refund_journal_id.default_account_id and refund_journal_id.default_account_id.id or False,
                                    # 'analytic_account_id': self.analytic_account_id.id,
                                    'quantity': 1,
                                    'price_unit': float(amount),
                                    'shopify_transaction_id': str(transaction_id)})]
                            }
                            refund_invoice = self.env['account.move'].sudo().create(
                                vals)
                        # refund_invoice.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True,
                        #                                                                                 recompute_tax_base_amount=True)
                        refund_invoice._check_balanced(container=False)
                    if not refund_invoice.shopify_transaction_id or refund_invoice.shopify_order_id:
                        refund_invoice.update(
                            {'shopify_transaction_id': str(transaction_id),
                             'shopify_config_id': self.shopify_config_id.id,
                             'shopify_order_id': self.shopify_order_id,
                             'sale_order_id': self.id,
                             'ref': 'Reversal of: %s' % self.shopify_order_name})
                    if self.shopify_config_id.is_refund_auto_paid:
                        if refund_invoice.state == 'draft':
                            refund_invoice.action_post()
                        self.create_shopify_order_payment(
                            transaction_dict, 'outbound')
                        payment_id = self.env['account.payment'].search([
                            ('shopify_order_id', '=', self.shopify_order_id),
                            ('shopify_config_id', '=', self.shopify_config_id.id),
                            ('sale_order_id', '=', self.id),
                            ('shopify_transaction_id', '=', str(transaction_id)),
                            ('payment_type', '=', 'outbound'),
                            ("state", '!=', 'cancelled')])
                        # for reconciled credit note
                        for rinv in refund_invoice:
                            if self.downpayment_history_ids:
                                rinv.update({'is_downpayment_refund': True})
                            move_lines = payment_id.move_id.invoice_line_ids.filtered(
                                lambda line: line.account_type in (
                                    'asset_receivable', 'liability_payable') and not line.reconciled)
                            for line in move_lines:
                                rinv.js_assign_outstanding_line(line.id)

    def create_shopify_order_payment(self, transaction_dict, payment_type='inbound'):
        """
            This method will use to create shopify order payment
            for unfulfilled order using transaction of shopify order
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        payment_obj = self.env['account.payment']
        journal_id = self.auto_workflow_id.pay_journal_id
        journal_payment_method = self.env.ref(
            'account.account_payment_method_manual_in')

        payment_method_line_ids = self.auto_workflow_id.pay_journal_id.inbound_payment_method_line_ids
        journal_payment_line_method = payment_method_line_ids.filtered(
            lambda i: i.payment_method_id.code == self.auto_workflow_id.in_pay_method_id.code)
        if journal_payment_line_method:
            journal_payment_method = journal_payment_line_method.payment_method_id
        if not self.partner_id.commercial_partner_id:
            self.partner_id._compute_commercial_partner()

        # shopify_transactions = shopify.Transaction().find(order_id=self.shopify_order_id)
        # for transaction in shopify_transactions:
        #     transaction_dict = transaction.to_dict()
        transaction_type = transaction_dict.get('transaction', {}).get(
            'kind') or transaction_dict.get('kind')
        status = transaction_dict.get('transaction', {}).get(
            'status') or transaction_dict.get('status')
        # if transactions are completed create payment else continue
        if transaction_type not in ['sale', 'refund', 'capture'] or status != 'success':
            return False
        transaction_id = transaction_dict.get('transaction', {}).get(
            'id') or transaction_dict.get('id')
        gateway = transaction_dict.get('transaction', {}).get(
            'gateway') or transaction_dict.get('gateway')
        amount = transaction_dict.get('transaction', {}).get(
            'amount') or transaction_dict.get('amount')
        local_inv_datetime = datetime.strptime(
            transaction_dict.get('processed_at')[:19],
            '%Y-%m-%dT%H:%M:%S')
        local_time = transaction_dict.get('processed_at')[
            20:].split(":")
        if transaction_dict.get('processed_at')[19] == "+":
            local_datetime = local_inv_datetime - timedelta(
                hours=int(local_time[0]),
                minutes=int(local_time[1]))
        else:
            local_datetime = local_inv_datetime + timedelta(
                hours=int(local_time[0]),
                minutes=int(local_time[1]))
        # Set payment date here
        payment_date = (str(local_datetime)[:19])
        existing_payment_id = payment_obj.search([
            ('shopify_transaction_id', '=', str(transaction_id)),
            ('shopify_config_id', '=', self.shopify_config_id.id),
            ("state", '!=', 'cancelled')], limit=1)
        if existing_payment_id:
            # TODO: need to added warning log for existing payment
            return True
        else:
            payment_vals = {'amount': amount,
                            'date': payment_date or self.date_order,
                            'payment_reference': self.name,
                            'partner_id': self.partner_id.commercial_partner_id.id,
                            'partner_type': 'customer',
                            'currency_id': self.currency_id.id,
                            'journal_id': journal_id.id,
                            'payment_type': payment_type,
                            'shopify_order_id': self.shopify_order_id,
                            'sale_order_id': self.id,
                            'payment_method_id': journal_payment_method.id or False,
                            'shopify_transaction_id': transaction_id or False,
                            'shopify_config_id': self.shopify_config_id.id,
                            'shopify_name': self.shopify_order_name or self.name or False,
                            'shopify_gateway': gateway or False}
            if transaction_type == 'refund':
                payment_vals.update({'payment_type': 'outbound'})
            else:
                payment_vals.update({'payment_type': 'inbound'})
            if transaction_type in ['sale', 'refund', 'capture'] and status == 'success':
                payment = payment_obj.create(payment_vals)
                payment.action_post()

    def process_unfulfillment_order(self, order_dict, shopify_config):
        """Using this method importing unfulfillment order from shopify into odoo"""
        workflow_id = self.auto_workflow_id if self.auto_workflow_id else self.env.ref(
            "bista_shopify_connector.automatic_workflow")
        if not workflow_id:
            raise UserError(_("Auto workflow not found."))
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        if workflow_id.register_payment:
            financial_status = order_dict.get('financial_status')
            fulfillment_status = order_dict.get('fulfillment_status')
            if not fulfillment_status and financial_status in ['paid', 'partially_paid']:
                if self.state in ['draft', 'sent'] and workflow_id.confirm_order:
                    self.action_confirm()
                if self.state in ['sale', 'done']:
                    ctx = {'shopify_order_id': self.shopify_order_id,
                           'shopify_log_id': shop_error_log_id,
                           'queue_line_id': queue_line_id}
                    if workflow_id.create_invoice:
                        ctx.update({'create_invoice': True,
                                    'journal_id': workflow_id.sale_journal_id.id})
                    if workflow_id.validate_invoice:
                        ctx.update({'validate_invoice': True})
                    if financial_status in ['paid', 'partially_paid', 'refunded', 'partially_refunded', 'authorized', 'overdue', 'voided']:
                        self.create_shopify_invoice(shopify_config)
                        self.create_shopify_direct_payment(
                            shopify_config, self, order_dict, self.partner_id)
                    shopify_transactions = shopify.Transaction().find(
                        order_id=str(self.shopify_order_id))
                    for transaction in shopify_transactions:
                        transaction_dict = transaction.to_dict()
                    self.create_shopify_order_payment(
                        transaction_dict, 'outbound')
            else:
                pass

    def process_auto_workflow(self, order_dict, shopify_config):
        """
            Using this method proccessing auto flow of odoo feature.
        """
        move_obj = self.env['account.move']
        workflow_id = self.auto_workflow_id if self.auto_workflow_id else self.env.ref(
            "bista_shopify_connector.automatic_workflow")
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        if not workflow_id:
            raise UserError(_("Auto workflow not found."))
        if self.state in ['draft', 'sent'] and workflow_id.confirm_order:
            self.action_confirm()
        if self.state == 'sale' or \
                (self.user_has_groups('sale.group_auto_done_setting') and self.state == 'done'):
            if self.picking_ids:
                team_id = self.env['crm.team'].search(
                    [('name', '=', 'Supply Chain')], limit=1)
                # [picking.write({'sales_team_id': team_id.id or False})
                #  for picking in self.picking_ids]
            if workflow_id.register_payment:
                # for create shopify order payment with unearned revenue flow
                tag_ids = self.create_shopify_order_tags_in_odoo(
                    order_dict.get('tags'))
                # self.update_fulfilment_details_to_order(self, shopify_config)
                # for create shopify order payment with unearned revenue flow
                if tag_ids and shopify_config.is_pay_unearned_revenue and tag_ids in shopify_config.shopify_tag_ids:
                    if order_dict.get('fulfillment_status') == 'fulfilled':
                        self.create_shopify_direct_payment(
                            shopify_config, self, order_dict, self.partner_id)
                    else:
                        self.create_shopify_payment(
                            shopify_config, self, order_dict, self.partner_id)
                        self.update({'is_unearned_revenue_order': True})
                else:
                    self.create_shopify_direct_payment(
                        shopify_config, self, order_dict, self.partner_id)
            # Process delivery orders/fulfillments
            ctx = {'shopify_order_id': self.shopify_order_id,
                   'shopify_log_id': shop_error_log_id,
                   'queue_line_id': queue_line_id}
            if workflow_id.create_invoice:
                ctx.update({'create_invoice': True,
                            'journal_id': workflow_id.sale_journal_id.id})
            if workflow_id.validate_invoice:
                ctx.update({'validate_invoice': True})
            fulfillment_status = order_dict.get('fulfillment_status')
            if fulfillment_status in ['fulfilled', 'partial']:
                self.with_context(ctx).process_shopify_order_fullfillment(
                    shopify_config,
                    fulfillment_status=fulfillment_status,
                    fulfillment_lines=order_dict.get(
                        'fulfillments',
                        []))
            financial_status = order_dict.get('financial_status')
            if financial_status in ['paid', 'refunded', 'partially_refunded', 'partially_paid', 'voided']:
                if self.is_manual_shopify_payment is False and self.is_manual_odoo_refund is False:
                    self.create_shopify_invoice(shopify_config)
                    self.create_shopify_direct_payment(
                        shopify_config, self, order_dict, self.partner_id)
            if workflow_id.register_payment:
                shopify_financial_status = order_dict.get('financial_status')
                fulfillment_status = order_dict.get('fulfillment_status')
                # for order and create payment for invoice
                if self.is_unearned_revenue_order:
                    if shopify_financial_status in ['refunded', 'partially_refunded']:
                        if not fulfillment_status:
                            # Fulfilled: Create credit note from unearned invoice if Unearned revenue flow
                            invoice_ids = self.downpayment_history_ids.mapped(
                                'invoice_id')
                            if invoice_ids:
                                out_invoice_ids = invoice_ids.filtered(
                                    lambda x: x.move_type == 'out_invoice' and x.payment_state in (
                                        'paid', 'in_payment'))
                                out_refund_invoice_ids = invoice_ids.filtered(
                                    lambda x: x.move_type == 'out_refund')
                                if out_invoice_ids and not out_refund_invoice_ids and invoice_ids:
                                    self.create_shopify_credit_note_in_odoo(
                                        invoice_ids)
                        elif fulfillment_status == 'partial':
                            move_obj.create_update_shopify_refund(order_dict,
                                                                  shopify_config)
                        elif fulfillment_status == 'fulfilled':
                            # Fulfilled: Create credit note from final invoice if Unearned revenue flow
                            invoice_ids = self.invoice_ids
                            if invoice_ids:
                                out_invoice_ids = invoice_ids.filtered(
                                    lambda x: x.move_type == 'out_invoice' and x.payment_state in (
                                        'paid', 'in_payment'))
                                out_refund_invoice_ids = invoice_ids.filtered(
                                    lambda x: x.move_type == 'out_refund')
                                if out_invoice_ids and not out_refund_invoice_ids and invoice_ids:
                                    self.create_shopify_credit_note_in_odoo(
                                        invoice_ids)
                else:
                    if self.is_manual_shopify_payment is False and self.is_manual_odoo_refund is False:
                        invoice_ids = self.invoice_ids
                        if shopify_financial_status in ['paid', 'refunded', 'partially_refunded', 'authorized',
                                                        'overdue', 'partially_paid', 'voided']:
                            # Unfulfilled: create payment for un-fulfil order
                            if not fulfillment_status:
                                shopify_transactions = shopify.Transaction().find(
                                    order_id=str(self.shopify_order_id))
                                for transaction in shopify_transactions:
                                    transaction_dict = transaction.to_dict()
                                self.create_shopify_order_payment(
                                    transaction_dict, 'outbound')
                            elif fulfillment_status == 'partial':
                                move_obj.create_update_shopify_refund(
                                    order_dict, shopify_config)
                            elif fulfillment_status == 'fulfilled' and invoice_ids:
                                self.create_shopify_credit_note_in_odoo(
                                    invoice_ids)

    def exiting_shopify_order_cancel(self, cancel_reason, existing_order_id):
        """Using this method cancel the exisitng shopify order in odoo"""
        existing_order_id.shopify_cancelled_at = existing_order_id.date_order
        existing_order_id.cancel_reason = cancel_reason if cancel_reason else f'Cancel Order is {existing_order_id.name}' or ''
        invoice_ids = existing_order_id.invoice_ids.filtered(
            lambda invoice: invoice.move_type == 'out_invoice')
        for invoice in invoice_ids:
            if invoice.payment_state == 'not_paid':
                invoice.button_draft()
                invoice.button_cancel()
        for picking in existing_order_id.picking_ids:
            if picking.state in ('draft', 'waiting', 'confirmed', 'assigned'):
                picking.action_cancel()
                self._cr.commit()
        existing_order_id._action_cancel()
        self._cr.commit()

    def shopify_order_cancel(self, cancel_reason, order_id):
        """
            This method is cancels the shopify order in odoo,
            make invoices and delivery cancel accordingly.
            @author: Yogeshwar Chaudhari @Bista Solutions Pvt. Ltd.
        """
        order_id.shopify_cancelled_at = order_id.date_order
        order_id.cancel_reason = cancel_reason if cancel_reason else f'Cancel Order is {order_id.name}' or ''
        invoice_ids = order_id.invoice_ids.filtered(
            lambda invoice: invoice.move_type == 'out_invoice')
        for invoice in invoice_ids:
            if invoice.payment_state == 'not_paid':
                invoice.button_draft()
                invoice.button_cancel()
        for picking in order_id.picking_ids:
            if picking.state in ('draft', 'waiting', 'confirmed', 'assigned'):
                picking.action_cancel()
                self._cr.commit()
        order_id.action_cancel()
        self._cr.commit()
        # sale_cancel_id = self.env['sale.order.cancel'].search([('order_id','=',order_id.id)])
        # if sale_cancel_id:
        #     sale_cancel = sale_cancel_id[0]
        #     sale_cancel.action_cancel()
        #     self._cr.commit()
        # elif picking.state=='done':
        #     line_ids = [(0, 0, {'product_id': line.product_id.id,
        #                         'quantity': line.quantity,
        #                         'return_line_reason':reason,
        #                         'uom_id': line.product_id.uom_id.id,
        #                         'move_id': line.id,
        #                         'lot_id': line.lot_id and line.lot_id.id or False,
        #                         }) for line in picking.move_ids_without_package]
        #     action = self.env['stock.return.picking'].create({
        #         'picking_id':picking.id,
        #         'product_return_moves':line_ids,
        #         'location_id': picking.location_id.id
        #     }).create_returns()
        #     pick_return = self.env["stock.picking"].browse(action["res_id"])
        #     pick_return.action_set_quantities_to_reservation()
        #     pick_return.button_validate()

    def update_shopify_orders_using_server_action(self, order_dict, shopify_config):
        """
            With the help of this method using server action we updating order.
        """
        shopify_config.check_connection()
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        financial_status = order_dict.get('financial_status')
        fulfillment_status = order_dict.get('fulfillment_status')
        try:
            if shopify_config.is_fetch_unfulfillment_order:
                if not fulfillment_status and financial_status in ['paid', 'partially_paid']:
                    shopify_order_id = order_dict.get('id')
                    cancelled_at = order_dict.get('cancelled_at')
                    cancel_reason = order_dict.get('cancel_reason')
                    ctx = {'shopify_log_id': shop_error_log_id,
                           'queue_line_id': queue_line_id}
                    existing_order_id = self.search([
                        ('shopify_order_id', '=', shopify_order_id),
                        ('shopify_config_id', '=', shopify_config.id)], limit=1)
                    existing_order_id.with_context(ctx)
                    if existing_order_id:
                        # TODO: Update Order
                        invoice_ids = existing_order_id.invoice_ids.filtered(
                            lambda invoice: invoice.move_type == 'out_invoice')
                        for invoice in invoice_ids:
                            if invoice and invoice.payment_state == 'not_paid':
                                invoice.button_draft()
                                invoice.button_cancel()
                                invoice.unlink()
                            else:
                                pass
                        location_warehouse_vals = self.get_shopify_warehouse_location(
                            order_dict, shopify_config)
                        tag_ids = self.create_shopify_order_tags_in_odoo(
                            order_dict.get('tags'))
                        self.update_fulfilment_details_to_order(
                            existing_order_id, shopify_config)
                        existing_order_id.update({
                            'warehouse_id': location_warehouse_vals['warehouse_id'].id,
                            'shopify_tag_ids': [(6, 0, tag_ids.ids)] if tag_ids else False
                        })
                        if cancelled_at:
                            existing_order_id.shopify_order_cancel(
                                cancelled_at, cancel_reason, existing_order_id)
                        else:
                            existing_order_id.with_context(
                                ctx).process_auto_workflow(order_dict, shopify_config)
                elif not fulfillment_status and financial_status in ['refunded', 'partially_refunded']:
                    shopify_order_id = order_dict.get('id')
                    cancelled_at = order_dict.get('cancelled_at')
                    cancel_reason = order_dict.get('cancel_reason')
                    refunds = order_dict.get('refunds')
                    ctx = {'shopify_log_id': shop_error_log_id,
                           'queue_line_id': queue_line_id}
                    existing_order_id = self.search([
                        ('shopify_order_id', '=', shopify_order_id),
                        ('shopify_config_id', '=', shopify_config.id)], limit=1)
                    existing_order_id.with_context(ctx)
                    if existing_order_id:
                        if cancelled_at:
                            existing_order_id.shopify_order_cancel(
                                cancelled_at, cancel_reason, existing_order_id)
                    else:
                        pass
                elif fulfillment_status and financial_status in ['paid', 'partially_paid']:
                    shopify_order_id = order_dict.get('id')
                    cancelled_at = order_dict.get('cancelled_at')
                    cancel_reason = order_dict.get('cancel_reason')
                    refunds = order_dict.get('refunds')
                    ctx = {'shopify_log_id': shop_error_log_id,
                           'queue_line_id': queue_line_id}
                    existing_order_id = self.search([
                        ('shopify_order_id', '=', shopify_order_id),
                        ('shopify_config_id', '=', shopify_config.id)], limit=1)
                    existing_order_id.with_context(ctx)
                    if existing_order_id:
                        # TODO: Update Order
                        if financial_status in ['paid', 'partially_paid']:
                            invoice_ids = existing_order_id.invoice_ids.filtered(
                                lambda invoice: invoice.move_type == 'out_invoice')
                            for invoice in invoice_ids:
                                if invoice and invoice.payment_state == 'not_paid':
                                    invoice.button_draft()
                                    invoice.button_cancel()
                                    invoice.unlink()
                                else:
                                    pass
                        location_warehouse_vals = self.get_shopify_warehouse_location(
                            order_dict, shopify_config)
                        tag_ids = self.create_shopify_order_tags_in_odoo(
                            order_dict.get('tags'))
                        self.update_fulfilment_details_to_order(
                            existing_order_id, shopify_config)
                        existing_order_id.update({
                            'warehouse_id': location_warehouse_vals['warehouse_id'].id,
                            'shopify_tag_ids': [(6, 0, tag_ids.ids)] if tag_ids else False
                        })
                        if cancelled_at:
                            existing_order_id.shopify_order_cancel(
                                cancelled_at, cancel_reason, existing_order_id)
                        else:
                            existing_order_id.with_context(
                                ctx).process_auto_workflow(order_dict, shopify_config)
                    else:
                        pass
                else:
                    pass
            else:
                shopify_order_id = order_dict.get('id')
                ctx = {'shopify_log_id': shop_error_log_id,
                       'queue_line_id': queue_line_id}
                existing_order_id = self.search([
                    ('shopify_order_id', '=', shopify_order_id),
                    ('shopify_config_id', '=', shopify_config.id)], limit=1)
                existing_order_id.with_context(ctx)
                if existing_order_id:
                    if financial_status in ['paid', 'partially_paid']:
                        invoice_ids = existing_order_id.invoice_ids.filtered(
                            lambda invoice: invoice.move_type == 'out_invoice')
                        for invoice in invoice_ids:
                            if invoice and invoice.payment_state == 'not_paid':
                                invoice.button_draft()
                                invoice.button_cancel()
                                invoice.unlink()
                            else:
                                pass
                    location_warehouse_vals = self.get_shopify_warehouse_location(
                        order_dict, shopify_config)
                    tag_ids = self.create_shopify_order_tags_in_odoo(
                        order_dict.get('tags'))
                    self.update_fulfilment_details_to_order(
                        existing_order_id, shopify_config)
                    existing_order_id.update({
                        'warehouse_id': location_warehouse_vals['warehouse_id'].id,
                        'shopify_tag_ids': [(6, 0, tag_ids.ids)] if tag_ids else False
                    })
                    if cancelled_at:
                        existing_order_id.shopify_order_cancel(
                            cancelled_at, cancel_reason, existing_order_id)
                    else:
                        existing_order_id.with_context(
                            ctx).process_auto_workflow(order_dict, shopify_config)
                else:
                    pass
        except Exception as e:
            error_message = 'Failed to import Orders : {}'.format(e)
            error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                   shopify_log_line_dict={'error': [
                                                       {'error_message': error_message,
                                                        'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

    def create_update_shopify_orders(self, order_dict, shopify_config):
        """
            Using this method we can create shopify order into odoo as well as updating existing order also.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        shopify_config.check_connection()
        error_log_env = self.env['shopify.error.log']
        risk_order_obj = self.env["shopify.risk.order"]
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        shopify_product_obj = self.env['shopify.product.template']
        shopify_product_variant_obj = self.env['shopify.product.product']
        discount_application = order_dict.get('discount_applications', False)
        shopify_order_created_date = order_dict.get('created_at')
        shopi_order_created_year = int(shopify_order_created_date[0:4])
        shopi_order_date = shopify_order_created_date[0:10]
        current_date = datetime.now()
        current_year = current_date.year
        if shopify_config.shopify_order_date and not (shopi_order_created_year >= current_year and shopi_order_date > shopify_config.shopify_order_date):
            return
        try:
            customer_name = False
            customer_data = order_dict.get('customer')
            shopify_customer_id = customer_data and customer_data.get(
                'id') or False
            partner_id = None
            if not customer_data and shopify_config.default_customer_id:
                partner_id = self.env.ref(
                    "bista_shopify_connector.shopify_partner") or shopify_config.default_customer_id
            if customer_data and shopify_customer_id:
                partner_id = self.get_customer(
                    shopify_customer_id, shopify_config, customer_data)
            if customer_data and customer_data.get('first_name') and customer_data.get('last_name'):
                customer_name = customer_data.get(
                    'first_name') + customer_data.get('last_name')
                if not partner_id:
                    raise UserError(
                        _("Customer [%s] not found,please import customer first." % customer_name))
            shopify_order_id = order_dict.get('id')
            existing_order_id = self.search([
                ('shopify_order_id', '=', shopify_order_id),
                ('shopify_config_id', '=', shopify_config.id),
                ('company_id', '=', shopify_config.default_company_id.id)], limit=1)
            shipping_addr_data = order_dict.get('shipping_address')
            shipping_addr_id = shipping_addr_data and self.create_shipping_or_billing_address(
                shipping_addr_data, parent_id=partner_id, atype='delivery') or partner_id
            billing_addr_data = order_dict.get('billing_address')
            billing_addr_id = billing_addr_data and self.create_shipping_or_billing_address(
                billing_addr_data, parent_id=partner_id, atype='invoice') or partner_id
            order_vals = self.prepare_order_vals(
                partner_id,
                billing_addr_id,
                shipping_addr_id,
                order_dict,
                shopify_config)
            shopify_line_items = order_dict.get('line_items')
            shopify_shipping_lines = order_dict.get('shipping_lines')
            taxes_included = order_dict.get('taxes_included')
            cancelled_at = order_dict.get('cancelled_at')
            cancel_reason = order_dict.get('cancel_reason')
            refunds = order_dict.get('refunds')
            shopify_total_price = order_dict.get(
                'total_price') and float(order_dict.get('total_price'))
            ctx = {'shopify_log_id': shop_error_log_id,
                   'queue_line_id': queue_line_id}
            existing_order_id.with_context(ctx)
            if existing_order_id:
                # TODO: Update Order
                location_warehouse_vals = self.get_shopify_warehouse_location(
                    order_dict, shopify_config)
                tag_ids = self.create_shopify_order_tags_in_odoo(
                    order_dict.get('tags'))
                self.update_fulfilment_details_to_order(
                    existing_order_id, shopify_config)
                existing_order_id.update({
                    'warehouse_id': location_warehouse_vals['warehouse_id'].id,
                    'shopify_tag_ids': [(6, 0, tag_ids.ids)] if tag_ids else False
                })
                if cancelled_at:
                    existing_order_id.exiting_shopify_order_cancel(
                        cancel_reason, existing_order_id)
                    # If cancelled_at and cancel reason, then cancel order in odoo
                    # cancel_datetime_utc = self.convert_date_utc(cancelled_at)
                    # existing_order_id.action_cancel()
                else:
                    # Method call for processing order based on auto workflow
                    existing_order_id.with_context(
                        ctx).process_auto_workflow(order_dict, shopify_config)
                # Process fulfillments for existing shopify orders. [Moved to process workflow]
                # if order_dict.get('fulfillment_status') == 'fulfilled':
                #     existing_order_id.with_context(shopify_order_id=shopify_order_id).process_shopify_order_fullfillment(shopify_config, fulfillment_status='fulfilled', fulfillment_lines=order_dict.get('fulfillments', []))
                # elif order_dict.get('fulfillment_status') == 'partial':
                #     existing_order_id.with_context(shopify_order_id=shopify_order_id).process_shopify_order_fullfillment(shopify_config, fulfillment_status='partial', fulfillment_lines=order_dict.get('fulfillments', []))
                if refunds:
                    self.create_return_pickings(
                        shopify_config, existing_order_id, refunds)
                # REMOVED ERROR LOG for successful import
                # error_log_env.create_update_log(
                #     shop_error_log_id=shop_error_log_id,
                #     shopify_log_line_dict={'success': [
                #         {'error_message': "Update Order %s Successfully" % shopify_order_id,
                #          'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                queue_line_id and queue_line_id.update(
                    {
                        'state': 'processed',
                        'order_id': existing_order_id.id,
                        'partner_id': existing_order_id.partner_id.id})
            else:
                # Create new order
                # Update Order vals with workflow data. If workflow not found,
                # raise error
                workflow_vals = self.prepare_workflow_vals(
                    order_dict, shopify_config)
                if workflow_vals:
                    order_vals.update(workflow_vals)
                # Prepare Sale order lines
                order_line_vals = []
                product_id = False
                for line in shopify_line_items:
                    shopify_line_id = line.get('id')
                    shopify_variant_id = line.get('variant_id')
                    shopify_product_id = line.get('product_id')
                    shopify_product_title = line.get('title')
                    discount_lines = line.get('discount_allocations', False)
                    qty = line.get('quantity')
                    price_unit = line.get('price')
                    sku = line.get('sku')
                    barcode = line.get('barcode')
                    price_qty = float(price_unit) * float(qty)
                    if shopify_variant_id:
                        shopify_product_product_id = self.get_product(
                            shopify_variant_id, shopify_product_id, shopify_config, sku, barcode)
                        # if shopify_product_product_id:
                        product_id = shopify_product_product_id.product_variant_id if shopify_product_product_id else False
                        if not product_id:
                            if shopify_config.is_create_product:
                                shopify_product_tmpl_id = shopify_product_obj.shopify_import_product_by_ids(
                                    shopify_config, shopify_product_id)
                                if shopify_product_tmpl_id:
                                    shopify_variant_id = shopify_product_variant_obj.search([
                                        ('product_variant_id',
                                         '=', shopify_variant_id),
                                        ('shopify_config_id',
                                         '=', shopify_config.id),
                                        ('shopify_product_template_id', '=', shopify_product_tmpl_id.id)], limit=1)
                                    product_id = shopify_product_tmpl_id.product_variant_id
                                else:
                                    if not shopify_config.is_create_product:
                                        product_id = self.env.ref(
                                            'bista_shopify_connector.shopify_product')
                                    else:
                                        raise UserError(
                                            _("Product [%s] not found,please import product first." % shopify_product_title))
                    else:
                        shopify_custom_product_name = line.get(
                            'name') and line.get('name').strip()
                        product_id = self.get_shopify_custom_product(
                            shopify_custom_product_name)
                        if not product_id:
                            raise UserError(
                                _("Custom Product [%s] not found in Shopify Product Mapping" % shopify_custom_product_name))
                        # custom_line = True
                    order_line_dict, tax_ids = self.prepare_order_line_vals(
                        line, product_id, taxes_included, shopify_config, shopify_line_id)
                    discount_percentage = 0.00
                    if discount_lines and discount_application:
                        for discount in discount_lines:
                            if discount_application[discount.get('discount_application_index')].get(
                                    'target_selection') in ['explicit', 'entitled']:
                                if discount_application[discount.get('discount_application_index')].get(
                                        'value_type') == 'fixed_amount':
                                    discount_percentage = self.calculate_discount_amount(
                                        discount_lines[0].get('amount'), price_qty)
                                elif discount_application[discount.get('discount_application_index')].get(
                                        'value_type') == 'percentage':
                                    discount_percentage = discount_application[0].get('value')
                    order_line_dict.update({"discount": discount_percentage})
                    order_line_vals.append((0, 0, order_line_dict))
                    if discount_application:
                        if any(dap.get('target_selection') == 'all' for dap in discount_application):
                            discount_line_dict = self.prepare_discount_line_vals(
                                product_id, order_dict.get('discount_codes'), tax_ids, shopify_config)
                            if len(discount_line_dict) > 0:
                                order_line_vals.append((0, 0, discount_line_dict))
                    # if discount_lines:
                    #     discount_line_dict = self.prepare_discount_line_vals(
                    #         product_id, discount_lines, tax_ids, shopify_config)
                    #     if len(discount_line_dict) > 0:
                    #         order_line_vals.append((0, 0, discount_line_dict))
                # prepare shipping lines in sale order lines
                for line in shopify_shipping_lines:
                    code = line['code']
                    title = line['title']
                    carrier_id = self.get_carrier(code, title, shopify_config)
                    shipping_line_dict = self.prepare_shipping_line_vals(
                        line, taxes_included, shopify_config)
                    order_line_vals.append((0, 0, shipping_line_dict))
                    order_vals.update({'carrier_id': carrier_id.id})

                order_id = False
                if order_line_vals:
                    location_warehouse_vals = self.get_shopify_warehouse_location(
                        order_dict, shopify_config)
                    order_vals.update({'order_line': order_line_vals,
                                       'warehouse_id': location_warehouse_vals['warehouse_id'].id})
                    if shopify_config.is_use_shop_seq:
                        shopify_order_name = order_dict.get('name')
                        order_vals.update({'name': shopify_order_name})
                    order_id = self.create(order_vals)
                    # Method call for checking rounding diff
                    self.check_rounding_diff(
                        order_id, shopify_total_price, shop_error_log_id, queue_line_id)

                    # order_id.action_confirm()[Moved to workflow process]
                    # for create shopify order payment with unearned revenue flow [Moved to workflow process]
                    # if shopify_config.is_pay_unearned_revenue:
                    #     self.create_shopify_payment(shopify_config, order_id, order_dict, partner_id)
                    # else:
                    #     self.create_shopify_direct_payment(shopify_config, order_id, order_dict, partner_id)

                    # Method call for processing order based on auto workflow
                    if cancelled_at:
                        self.shopify_order_cancel(
                            cancelled_at, cancel_reason, order_id)
                        # If cancelled_at and cancel reason, then cancel order in odoo
                        # cancel_datetime_utc = self.convert_date_utc(cancelled_at)
                        # existing_order_id.action_cancel()
                    else:
                        order_id.with_context(ctx).process_auto_workflow(
                            order_dict, shopify_config)
                        # Process delivery orders/fulfillments [Moved to workflow process]
                        # if order_dict.get('fulfillment_status') == 'fulfilled':
                        #     order_id.with_context(shopify_order_id=shopify_order_id).process_shopify_order_fullfillment(shopify_config, fulfillment_status='fulfilled', fulfillment_lines=order_dict.get('fulfillments', []))
                        # elif order_dict.get('fulfillment_status') == 'partial':
                        #     order_id.with_context(shopify_order_id=shopify_order_id).process_shopify_order_fullfillment(shopify_config, fulfillment_status='partial', fulfillment_lines=order_dict.get('fulfillments', []))
                    if refunds:
                        self.create_return_pickings(
                            shopify_config, order_id, refunds)
                else:
                    # TODO
                    pass
                risk_response = shopify.OrderRisk().find(order_id=shopify_order_id)
                if risk_response:
                    for risk in risk_response:
                        risk_order = risk.to_dict()
                        sale_order = existing_order_id or order_id
                        is_risk_order = risk_order_obj.create_risk_order_line_in_odoo(
                            risk_order, sale_order)
                        if is_risk_order:
                            sale_order.is_risk_order = True
                # REMOVED ERROR LOG for successful import
                # error_log_env.create_update_log(
                #     shop_error_log_id=shop_error_log_id,
                #     shopify_log_line_dict={'success': [
                #         {'error_message': "Import Order %s Successfully" % shopify_order_id,
                #          'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                queue_line_id and queue_line_id.update(
                    {
                        'state': 'processed',
                        'order_id': order_id and order_id.id,
                        'partner_id': order_id and order_id.partner_id.id})
        except Exception as e:
            error_message = 'Failed to import Orders : {}'.format(e)
            error_log_env.create_update_log(
                shop_error_log_id=shop_error_log_id,
                shopify_log_line_dict={
                    'error': [
                        {
                            'error_message': error_message,
                            'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.write({'state': 'failed'})

    def calculate_discount_percentage(self, order_data):
        """Extract values from the order_data dictionary"""
        total_line_items_price = float(order_data["total_line_items_price"])
        current_total_discounts = float(order_data["current_total_discounts"])
        discount_percentage = (current_total_discounts /
                               total_line_items_price) * 100
        return discount_percentage

    # def process_return_order(self, order_dict, shopify_config):
    #     error_log_env = self.env['shopify.error.log']
    #     shop_error_log_id = self.env.context.get('shopify_log_id', False)
    #     queue_line_id = self.env.context.get('queue_line_id', False)
    #     if not shop_error_log_id:
    #         shop_error_log_id = error_log_env.create_update_log(
    #             shopify_config_id=shopify_config, operation_type='import_return')
    #     try:
    #         shopify_order_id = order_dict.get('id')
    #         refunds = order_dict.get('refunds')
    #         order_id = self.search([
    #             ('shopify_order_id', '=', shopify_order_id),
    #             ('shopify_config_id', '=', shopify_config.id),
    #             ('company_id', '=', shopify_config.default_company_id.id)], limit=1)
    #         if not order_id:
    #             raise UserError(
    #                 _('Order not found with Shopify Order ID %s.' % shopify_order_id))
    #         if refunds:
    #             self.create_return_pickings(shopify_config, order_id, refunds)
    #         queue_line_id and queue_line_id.update(
    #             {'state': 'processed', 'order_id': order_id.id,
    #              'partner_id': order_id.partner_id.id})
    #     except Exception as e:
    #         # raise
    #         error_message = 'Failed to import Return Orders : {}'.format(e)
    #         error_log_env.create_update_log(
    #             shop_error_log_id=shop_error_log_id,
    #             shopify_log_line_dict={
    #                 'error': [
    #                     {
    #                         'error_message': error_message,
    #                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
    #         queue_line_id and queue_line_id.write({'state': 'failed'})

    # def process_return_order(self, order_dict, shopify_config):
    #     error_log_env = self.env['shopify.error.log']
    #     shop_error_log_id = self.env.context.get('shopify_log_id', False)
    #     queue_line_id = self.env.context.get('queue_line_id', False)
    #     if not shop_error_log_id:
    #         shop_error_log_id = error_log_env.create_update_log(
    #             shopify_config_id=shopify_config, operation_type='import_return')
    #     try:
    #         shopify_order_id = order_dict.get('id')
    #         refunds = order_dict.get('refunds')
    #         order_id = self.search([
    #             ('shopify_order_id', '=', shopify_order_id),
    #             ('shopify_config_id', '=', shopify_config.id),
    #             ('company_id', '=', shopify_config.default_company_id.id)], limit=1)
    #         if not order_id:
    #             raise UserError(
    #                 _('Order not found with Shopify Order ID %s.' % shopify_order_id))
    #         if refunds:
    #             self.create_return_pickings(shopify_config, order_id, refunds)
    #         queue_line_id and queue_line_id.update(
    #             {'state': 'processed', 'order_id': order_id.id,
    #              'partner_id': order_id.partner_id.id})
    #     except Exception as e:
    #         # raise
    #         error_message = 'Failed to import Return Orders : {}'.format(e)
    #         error_log_env.create_update_log(
    #             shop_error_log_id=shop_error_log_id,
    #             shopify_log_line_dict={
    #                 'error': [
    #                     {
    #                         'error_message': error_message,
    #                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
    #         queue_line_id and queue_line_id.write({'state': 'failed'})

    def process_return_order(self, order_dict, shopify_config):
        """
            This method is used to create the return for the shopify order.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        if not shop_error_log_id:
            shop_error_log_id = error_log_env.sudo().create_update_log(
                shopify_config_id=shopify_config, operation_type='import_return')
        try:
            if self.is_manual_shopify_payment is False and self.is_manual_odoo_refund is False:
                shopify_order_id = order_dict.get('id')
                refunds = order_dict.get('refunds')
                order_id = self.search([
                    ('shopify_order_id', '=', shopify_order_id),
                    ('shopify_config_id', '=', shopify_config.id),
                    ('company_id', '=', shopify_config.default_company_id.id)], limit=1)
                if not order_id:
                    raise UserError(
                        _('Order not found with Shopify Order ID %s.' % shopify_order_id))
                if refunds:
                    if self.is_manual_shopify_payment is False and self.is_manual_odoo_refund is False:
                        self.create_return_pickings(
                            shopify_config, order_id, refunds)
                queue_line_id and queue_line_id.sudo().update(
                    {'state': 'processed', 'order_id': order_id.id,
                     'partner_id': order_id.partner_id.id})
            else:
                pass
        except Exception as e:
            error_message = f'Failed to import Return Orders : {format(e)}.'
            error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                   shopify_log_line_dict={'error': [
                                                       {'error_message': error_message,
                                                        'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.sudo().write({'state': 'failed'})

    def create_shopify_direct_payment(self, shopify_config, exist_order, order_dict, partner_id):
        """
            This method is creating payment in odoo based on shopify transactions.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        currency_obj = self.env['res.currency']
        error_log_env = self.env['shopify.error.log'].sudo()
        if not order_dict:
            financial_status = exist_order.financial_workflow_id.financial_status
            shop_order_id = exist_order.shopify_order_id
            order_name = exist_order.shopify_order_name
        else:
            financial_status = order_dict and order_dict.get(
                'financial_status')
            shop_order_id = order_dict.get('id')
            order_name = order_dict.get('name')
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        payment_obj = self.env['account.payment']
        inv_obj = self.env['account.move'].sudo()
        # payment_method_in = self.env.ref(
        #     "account.account_payment_method_manual_in")
        journal_sale = self.env['account.journal'].search(
            [('type', '=', 'sale'),
             ('company_id', '=', shopify_config.default_company_id.id)],
            limit=1)
        try:
            if exist_order and financial_status in ('paid', 'partially_paid',
                                                    'refunded', 'partially_refunded'):
                transactions = shopify.Transaction.find(order_id=shop_order_id)
                payment_date = exist_order.date_order or False
                for transaction in transactions:
                    transaction_data = transaction.attributes
                    transaction_id = transaction_data.get('id')
                    status = transaction_data.get('status')
                    kind = transaction_data.get('kind')
                    msg = transaction_data.get('message')
                    gateway = transaction_data.get('gateway')
                    existing_payment_id = payment_obj.search(
                        [('shopify_transaction_id', '=', str(transaction_id)),
                         ('shopify_config_id', '=', shopify_config.id),
                         ("state", '!=', 'cancelled'),
                         ], limit=1)
                    if existing_payment_id:
                        continue
                    if status == 'success' and kind in ['sale', 'capture']:
                        amount = transaction_data.get('amount')
                        local_inv_datetime = datetime.strptime(
                            transaction_data.get('processed_at')[:19],
                            '%Y-%m-%dT%H:%M:%S')
                        local_time = transaction_data.get('processed_at')[
                            20:].split(":")
                        if transaction_data.get('processed_at')[19] == "+":
                            local_datetime = local_inv_datetime - timedelta(
                                hours=int(local_time[0]),
                                minutes=int(local_time[1]))
                        else:
                            local_datetime = local_inv_datetime + timedelta(
                                hours=int(local_time[0]),
                                minutes=int(local_time[1]))
                        # Set payment date here
                        payment_date = (str(local_datetime)[:19])
                        # Check payment currency
                        tcurrency = transaction_data.get('currency')
                        tcurrency_id = currency_obj.search(
                            [('name', '=', tcurrency)], limit=1)
                        if not tcurrency_id:
                            error_message = "Currency %s not found in the system for transaction %s. " \
                                "Please contact system Administrator." % (
                                    tcurrency, transaction_id)
                            error_log_env.sudo().create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={'error': [
                                    {'error_message': error_message,
                                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

                            continue
                        # TODO: Update it once we implement workflow
                        auto_workflow_id = self.auto_workflow_id
                        journal_id = auto_workflow_id.pay_journal_id
                        if not journal_id:
                            error_message = 'Payment journal not found!'
                            error_log_env.sudo().create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={'error': [
                                    {'error_message': error_message,
                                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                            continue
                        payment_method_id = auto_workflow_id.in_pay_method_id
                        if not self.partner_id.commercial_partner_id:
                            self.partner_id._compute_commercial_partner()
                        payment_type = 'inbound'
                        if kind == 'refund':
                            payment_type = 'outbound'

                        invoice = inv_obj.search([('shopify_order_id', '=', str(shop_order_id)),
                                                  ('sale_order_id', '=', self.id),
                                                  ('is_downpayment_inv', '=', True),
                                                  ('move_type', '=', 'out_invoice')], limit=1)
                        if not invoice:
                            invoice = self.invoice_ids
                        # if not invoice:
                        #     invoice = exist_order.manual_create_downpayment_invoice(
                        #         movetype='out_invoice', amount=amount)
                        if not invoice:
                            # TODO: need to add warning for it
                            continue
                        invoice.update({
                            'journal_id': journal_sale.id,
                            'shopify_config_id': shopify_config.id,
                            'shopify_order_id': exist_order.shopify_order_id})

                        invoice = exist_order.invoice_ids.filtered(
                            lambda i: i.state != 'cancel' and i.move_type == 'out_invoice' and i.payment_state != 'paid')
                        # if len(invoice) > 1:
                        #     inv_ids = invoice.ids
                        # else:
                        #     inv_ids = [invoice.id]
                        # payment_vals = {'amount': amount,
                        #                 'date': payment_date,
                        #                 'payment_reference': self.name,
                        #                 'partner_id': partner_id.id,
                        #                 'partner_type': 'customer',
                        #                 'currency_id': tcurrency_id.id,
                        #                 'journal_id': journal_id and journal_id.id,
                        #                 'payment_type': payment_type,
                        #                 'shopify_order_id': shop_order_id,
                        #                 'sale_order_id': self.id,
                        #                 'payment_method_id': payment_method_id.id or False,
                        #                 'shopify_transaction_id': transaction_id or False,
                        #                 'shopify_gateway': gateway or False,
                        #                 'shopify_note': msg,
                        #                 'shopify_name': order_name,
                        #                 'shopify_config_id': shopify_config.id,
                        #                 'move_id': invoice.id}
                        # payment = payment_obj.create(payment_vals)
                        #     payment.action_post()
                        if kind in ['sale', 'refund', 'capture'] and status == 'success':
                            reg_payment = self.env['account.payment.register'].with_context(
                                active_model='account.move', active_ids=invoice.ids).create(
                                {
                                    'payment_date': invoice.date,
                                    'communication': invoice.name,
                                    'amount': amount,
                                    'journal_id': journal_id.id
                                }
                            )._create_payments()
                            if reg_payment:
                                reg_payment.write({
                                    'sale_order_id': exist_order.id,
                                    'shopify_order_id': shop_order_id,
                                    'shopify_transaction_id': transaction_id or False,
                                    'shopify_gateway': gateway or False,
                                    'shopify_note': msg,
                                    'shopify_name': order_name,
                                    'shopify_config_id': shopify_config.id,
                                })
        except Exception as e:
            error_message = 'Failed to create payment: {}'.format(e)
            error_log_env.sudo().create_update_log(
                shop_error_log_id=shop_error_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': error_message,
                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

    def invoice_payment_reconciled_amount(self, payment_ids):
        """
            This method will return amount of un-reconciled line for payments
            @return : amount_lines
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        amount_lines = 0.00
        for payment in payment_ids:
            move_lines = payment.move_id.invoice_line_ids.filtered(
                lambda line: line.account_type in (
                    'asset_receivable', 'liability_payable') and not line.reconciled)
            for line in move_lines:
                amount_lines += abs(line.amount_residual)
        return amount_lines

    def create_rounding_diff(self, invoice, diff_amount_residual):
        """
            This method will create rounding diff line in shopify invoice.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        diff_product = self.env.ref(
            'bista_shopify_connector.shopify_rounding_diff_product')
        rounding_diff_account_id = self.shopify_config_id.rounding_diff_account_id
        # added for round diff create line
        round_qty = 0
        if diff_amount_residual in [-0.01, -0.02]:
            round_qty = 1
        elif diff_amount_residual in [0.01, 0.02]:
            round_qty = -1
        if round_qty != 0:
            invoice.with_context(check_move_validity=False).write(
                {'invoice_line_ids': [(0, 0, {
                    'product_id': diff_product.id,
                    'name': 'Rounding Difference %s' % self.name,
                    'account_id': rounding_diff_account_id.id,
                    # 'analytic_account_id': self.analytic_account_id.id,
                    'quantity': round_qty,
                    'price_unit': abs(diff_amount_residual)})],
                    'is_rounding_diff': True})

    def create_shopify_invoice(self, shopify_config):
        """
            This method will create shopify invoices based on fulfillment.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        if not shop_error_log_id:
            shop_error_log_id = error_log_env.sudo().create_update_log(
                shopify_config_id=shopify_config,  operation_type='import_order')
        journal_id = self._context.get('journal_id')
        if not journal_id:
            journal_id = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', shopify_config.default_company_id.id)],
                                                            limit=1).id
        for order in self:
            context = {
                'active_model': 'sale.order',
                'active_ids': order.ids,
                'active_id': order.id,
                'default_journal_id': journal_id,
                # 'default_deposit_account_id': shopify_config.unearned_account_id.id,
                'default_account_id': shopify_config.unearned_account_id.id or self.partner_id.property_account_receivable_id.id,
                'default_shopify_config_id': shopify_config.id,
                'default_sale_order_id': order.id,
                'shopify_order_id': order.shopify_order_id,
                'open_invoices': False
            }
            adv_invoice_id = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'delivered',
                'deduct_down_payments': True,
                # 'fixed_amount': amount,
                # 'deposit_account_id': shopify_config.unearned_account_id.id,
            })
            adv_invoice_id.with_context(default_shopify_order_id=order.shopify_order_id,
                                        default_invoice_date=order.date_order,
                                        ).create_invoices()
            # order.invoice_ids.filtered(
            #     lambda r: r.state == 'draft').action_post()
            for inv in order.invoice_ids.filtered(lambda iv: iv.move_type == 'out_invoice' and iv.payment_state != 'paid' and iv.state != 'cancel'):
                if inv.amount_residual > 0.0 and not order.is_unearned_revenue_order:
                    # for final invoice reconciled
                    # payment_ids = self.env['account.payment'].search(
                    #     [('sale_order_id', '=', self.id),
                    #      ('shopify_order_id', '=', self.shopify_order_id),
                    #      ('shopify_config_id', '=', shopify_config.id),
                    #      ("state", '!=', 'cancelled')])
                    payment_ids = self.env['account.payment'].search(
                        [('shopify_order_id', '=', order.shopify_order_id),
                         ('shopify_config_id', '=', shopify_config.id),
                         ("state", '!=', 'cancelled')])
                    if payment_ids:
                        amount_lines = order.invoice_payment_reconciled_amount(
                            payment_ids)
                        # added for round diff create line unearned revenue flow
                        diff_amount_residual = round(
                            inv.amount_residual - float(amount_lines), 5)
                        # order.create_rounding_diff(inv, diff_amount_residual)
                        # end rounding diff code
                    inv.filtered(lambda r: r.state == 'draft').action_post()
                    for payment in payment_ids:
                        move_lines = payment.move_id.invoice_line_ids.filtered(
                            lambda line: line.account_type in (
                                'asset_receivable', 'liability_payable') and not line.reconciled)
                        for line in move_lines:
                            inv.js_assign_outstanding_line(line.id)
                    if inv.amount_residual > 0.0:
                        error_log_env.sudo().create_update_log(
                            shop_error_log_id=shop_error_log_id,
                            shopify_log_line_dict={'error': [
                                {'error_message': "Please process an invoice %s for order %s manually, as it is "
                                                  "not completely paid." % (
                                                      inv.name, order.name),
                                 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                else:
                    moves_creditnote = False
                    if order.remaining_downpayment > 0:
                        dp_amount = order.remaining_downpayment
                        if dp_amount > inv.amount_total:
                            dp_amount = inv.amount_total
                        # added for round diff create line unearned revenue flow
                        diff_amount_residual = round(
                            inv.amount_residual - dp_amount, 5)
                        order.create_rounding_diff(inv, diff_amount_residual)
                        # end rounding diff code
                        # if dp_amount > 0:
                        #     moves_creditnote = order.manual_create_downpayment_invoice(
                        #         movetype='out_refund', amount=dp_amount)
                    inv.filtered(lambda r: r.state == 'draft').action_post()
                    if moves_creditnote:
                        lines = inv.line_ids.filtered(
                            lambda x: (
                                x.account_id.reconcile or x.account_id.internal_type == 'liquidity')
                            and not x.reconciled)
                        for line in lines:
                            counterpart_lines = moves_creditnote.line_ids.filtered(
                                lambda x: x.account_id == line.account_id
                                and x.currency_id == line.currency_id
                                and not x.reconciled)
                            (line + counterpart_lines).reconcile()
                    if inv.amount_residual > 0.0:
                        error_log_env.sudo().create_update_log(
                            shop_error_log_id=shop_error_log_id,
                            shopify_log_line_dict={'error': [
                                {'error_message': "Please process an invoice %s for order %s manually, as it is "
                                 "not completely paid." % (
                                     inv.name, order.name),
                                    'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

    def create_shopify_payment(self, shopify_config, exist_order, order_dict, partner_id):
        """
           This method is creating payment based on transactions.
           @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
       """
        currency_obj = self.env['res.currency']
        error_log_env = self.env['shopify.error.log'].sudo()
        financial_status = order_dict.get('financial_status')
        shop_order_id = order_dict.get('id')
        order_name = order_dict.get('name')
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        payment_obj = self.env['account.payment'].sudo()
        inv_obj = self.env['account.move'].sudo()
        auto_workflow_id = self.auto_workflow_id
        journal_id = auto_workflow_id.pay_journal_id
        if not journal_id:
            error_message = 'Payment journal not found!'
            error_log_env.sudo().create_update_log(
                shop_error_log_id=shop_error_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': error_message,
                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
        payment_method_id = auto_workflow_id.in_pay_method_id
        # TODO: if want to set with batch payment type
        # payment_method_in = self.env.ref(
        #     'account_batch_payment.account_payment_method_batch_deposit')
        journal_sale = self.env['account.journal'].search(
            [('type', '=', 'sale'),
             ('company_id', '=', shopify_config.default_company_id.id)],
            limit=1)
        if exist_order and financial_status in ('paid', 'partially_paid',
                                                'refunded', 'partially_refunded'):
            transactions = []
            # try: TODO: need to add time sleep for resolved multiple call error
            transactions = shopify.Transaction.find(order_id=shop_order_id)
            # except Exception as e:
            #     if e and e.response.code == 429 and e.response.msg == "Too Many Requests":
            #         time.sleep(5)
            #         transactions = shopify.Transaction.find(
            #             order_id=shop_order_id)
            payment_date = exist_order.date_order or False
            for transaction in transactions:
                transaction_data = transaction.attributes
                transaction_id = transaction_data.get('id')
                status = transaction_data.get('status')
                kind = transaction_data.get('kind')
                msg = transaction_data.get('message')
                gateway = transaction_data.get('gateway')
                if status == 'success' and kind in ['sale', 'capture']:
                    amount = transaction_data.get('amount')
                    local_inv_datetime = datetime.strptime(
                        transaction_data.get('processed_at')[:19],
                        '%Y-%m-%dT%H:%M:%S')
                    local_time = transaction_data.get('processed_at')[
                        20:].split(":")
                    if transaction_data.get('processed_at')[19] == "+":
                        local_datetime = local_inv_datetime - timedelta(
                            hours=int(local_time[0]),
                            minutes=int(local_time[1]))
                    else:
                        local_datetime = local_inv_datetime + timedelta(
                            hours=int(local_time[0]),
                            minutes=int(local_time[1]))
                    # Set payment date here
                    payment_date = (str(local_datetime)[:19])
                    # Check payment currency
                    tcurrency = transaction_data.get('currency')
                    tcurrency_id = currency_obj.search(
                        [('name', '=', tcurrency)], limit=1)
                    if not tcurrency_id:
                        error_message = "Currency %s not found in the system for transaction %s. " \
                            "Please contact system Administrator." % (
                                tcurrency, transaction_id)
                        error_log_env.sudo().create_update_log(
                            shop_error_log_id=shop_error_log_id,
                            shopify_log_line_dict={'error': [
                                {'error_message': error_message,
                                 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

                        continue
                    invoice = inv_obj.search([('shopify_order_id', '=', str(shop_order_id)),
                                              ('sale_order_id', '=', self.id),
                                              ('is_downpayment_inv', '=', True),
                                              ('move_type', '=', 'out_invoice')], limit=1)
                    # if not invoice:
                    #     invoice = exist_order.manual_create_downpayment_invoice(
                    #         movetype='out_invoice', amount=amount)
                    if not invoice:
                        # TODO: need to add warning for it
                        continue
                    invoice.update({
                        'journal_id': journal_sale.id,
                        # 'deposit_account_id': shopify_config.unearned_account_id.id,
                        # 'account_id': shopify_config.unearned_account_id.id,
                        'shopify_config_id': shopify_config.id,
                        'shopify_order_id': exist_order.shopify_order_id})

                    payments = payment_obj.search([(
                        'shopify_transaction_id', '=', transaction_id),
                        ('shopify_config_id', '=', shopify_config.id),
                        ("state", '!=', 'cancelled')])
                    # ('invoice_ids', 'in', invoice.ids)
                    if not payments:
                        # if len(invoice) > 1:
                        #     inv_ids = invoice.ids
                        # else:
                        #     inv_ids = [invoice.id]
                        # fields_lst = [
                        #     'state',
                        #     'reconciled_invoices_count',
                        #     'has_invoices',
                        #     'move_reconciled',
                        #     'id',
                        #     'name',
                        #     # 'invoice_ids',
                        #     'payment_type',
                        #     'partner_type',
                        #     'partner_id',
                        #     'company_id',
                        #     'amount',
                        #     'journal_id',
                        #     'destination_journal_id',
                        #     'hide_payment_method',
                        #     'payment_method_id',
                        #     'payment_method_code',
                        #     'payment_token_id',
                        #     'partner_bank_account_id',
                        #     'show_partner_bank_account',
                        #     'require_partner_bank_account',
                        #     'payment_transaction_id',
                        #     'currency_id',
                        #     'payment_date',
                        #     'payment_reference',
                        #     'payment_difference',
                        #     'payment_difference_handling',
                        #     'writeoff_account_id',
                        #     'writeoff_label',
                        #     'message_follower_ids',
                        #     'activity_ids',
                        #     'message_ids',
                        #     'message_attachment_count']
                        # payment_vals = payment_obj.with_context(
                        #     active_ids=inv_ids,
                        #     active_model='account.move').default_get(
                        #     fields_lst)
                        payment_vals = {
                            'journal_id': journal_id.id,
                            'amount': amount,
                            'partner_id': partner_id.id,
                            'currency_id': tcurrency_id.id,
                            'date': payment_date,
                            'payment_reference': self.name,
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'payment_method_id': payment_method_id.id,
                            'shopify_transaction_id': transaction_id,
                            'shopify_note': msg,
                            'shopify_gateway': gateway,
                            'shopify_order_id': shop_order_id,
                            'shopify_name': order_name,
                            'shopify_config_id': shopify_config.id,
                            'move_id': invoice
                        }
                        payment = payment_obj.create(
                            payment_vals)
                        payment.action_post()
                        move_lines = payment.line_ids.filtered(
                            lambda line: line.account_type in (
                                'asset_receivable',
                                'liability_payable') and not line.reconciled)
                        for line in move_lines:
                            invoice.js_assign_outstanding_line(line.id)

            return True

    def fetch_all_shopify_orders(self, from_order_date=False, to_order_date=False,
                                 is_fetch_unfulfillment_order=False):
        """
           This method will featch shopify orders.
           @return: shopify draft order list
           @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        try:
            shopify_draft_order_list = []
            page_info = False
            status = 'any'
            if is_fetch_unfulfillment_order:
                status = 'unfulfilled'
            while 1:
                if from_order_date and to_order_date:
                    if page_info:
                        # page_wise_draft_order_list = shopify.Order().find(
                        #     limit=150, page_info=page_info, status='any')
                        page_wise_draft_order_list = shopify.Order().find(
                            limit=150, page_info=page_info)
                    else:
                        page_wise_draft_order_list = shopify.Order().find(
                            updated_at_min=from_order_date,
                            updated_at_max=to_order_date,
                            limit=150, status=status)
                else:
                    if page_info:
                        page_wise_draft_order_list = shopify.Order().find(
                            limit=150, page_info=page_info)
                    else:
                        page_wise_draft_order_list = shopify.Order().find(
                            limit=150, status=status)
                page_url = page_wise_draft_order_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and \
                    parsed.get('page_info', False)[0] or False
                shopify_draft_order_list += page_wise_draft_order_list
                if not page_info:
                    break
            return shopify_draft_order_list
        except Exception as e:
            raise AccessError(e)

    def shopify_import_order_by_ids_using_server_action(self, shopify_config, shopify_order_by_ids):
        """ TODO: Create queue and then process it like import orders """
        shopify_config.check_connection()
        error_log_env = self.env['shopify.error.log'].sudo()
        order_list = []
        shopify_log_line_dict = self.env.context.get('shopify_log_line_dict',
                                                     {'error': [], 'success': []})
        shopify_log_id = error_log_env.sudo().create_update_log(
            shopify_config_id=shopify_config,
            operation_type='import_order_by_ids')
        for order in ''.join(shopify_order_by_ids.split()).split(','):
            try:
                order_list.append(shopify.Order().find(order))
            except:
                raise ValidationError(
                    'Order Not Found! Please enter valid Order ID!')
        for shopify_order in order_list:
            shopify_order_dict = shopify_order.to_dict()
            gateway = self.fetch_gateway_from_transaction(
                shopify_order_dict.get('id'))
            if not self.check_shopify_gateway(gateway, shopify_config):
                self.create_shopify_payment_gateway(gateway, shopify_config)
            self.with_context(shopify_log_line_dict=shopify_log_line_dict,
                              shopify_log_id=shopify_log_id).update_shopify_orders_using_server_action(shopify_order_dict, shopify_config)
        # if not shopify_log_id.shop_error_log_line_ids and not self.env.context.get('shopify_log_id', False):
        #     shopify_log_id and shopify_log_id.unlink()

    def shopify_authorised_order_cron(self):
        """ Cron For Authorised Order """
        sale_ids = self.search(
            [('shopify_financial_status', '=', 'authorized')])
        sale_ids = sale_ids.filtered(lambda x: x.shopify_financial_status == 'authorized'
                                     and x.shh_payment_status == 'not_paid'
                                     and x.shopify_order_id)
        if sale_ids:
            for sale_id in sale_ids:
                self.shopify_import_order_by_ids_using_server_action(
                    sale_id.shopify_config_id, sale_id.shopify_order_id)

    def shopify_import_order_by_ids(self, shopify_config, shopify_order_by_ids):
        """ TODO: Create queue and then process it like import orders """
        shopify_config.check_connection()
        error_log_env = self.env['shopify.error.log'].sudo()
        order_list = []
        shopify_log_line_dict = self.env.context.get('shopify_log_line_dict',
                                                     {'error': [], 'success': []})
        shopify_log_id = error_log_env.sudo().create_update_log(
            shopify_config_id=shopify_config,
            operation_type='import_order_by_ids')
        for order in ''.join(shopify_order_by_ids.split()).split(','):
            try:
                order_list.append(shopify.Order().find(order))
            except:
                raise ValidationError(
                    'Order Not Found! Please enter valid Order ID!')
        for shopify_order in order_list:
            shopify_order_dict = shopify_order.to_dict()
            gateway = self.fetch_gateway_from_transaction(
                shopify_order_dict.get('id'))
            if not self.check_shopify_gateway(gateway, shopify_config):
                self.create_shopify_payment_gateway(gateway, shopify_config)
            self.with_context(shopify_log_line_dict=shopify_log_line_dict,
                              shopify_log_id=shopify_log_id).create_update_shopify_orders(shopify_order_dict, shopify_config)
        # if not shopify_log_id.shop_error_log_line_ids and not self.env.context.get('shopify_log_id', False):
        #     shopify_log_id and shopify_log_id.unlink()
        # return shopify_product_template_id

    def shopify_import_return_orders(self, shopify_config):
        """
            This method is used to create queue and queue line for orders.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = error_log_env.sudo().create_update_log(
            shopify_config_id=shopify_config, operation_type='import_return')
        shopify_config.check_connection()
        from_order_date = shopify_config.last_return_order_import_date or fields.Datetime.now()
        to_order_date = fields.Datetime.now()
        shopify_order_list = self.fetch_all_shopify_orders(
            from_order_date, to_order_date)
        if shopify_order_list:
            for shopify_orders in tools.split_every(150, shopify_order_list):
                shop_queue_id = shopify_config.action_create_queue(
                    'import_return')
                for order in shopify_orders:
                    order_dict = order.to_dict()
                    if not order_dict.get('refunds'):
                        shopify_order_number = order_dict.get('order_number')
                        error_message = 'Please make sure while importing return orders for {}, you should have refund order then you can able to import the order.'.format(
                            shopify_order_number)
                        error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                               shopify_log_line_dict={'error': [
                                                                   {'error_message': error_message}]})
                        continue
                    refund_data = order_dict.get('refunds')
                    if not all(refund_line.get('restock') for refund_line in refund_data):
                        continue
                    name = order_dict.get('name', '')
                    line_vals = {
                        'shopify_id': order_dict.get('id') or '',
                        'state': 'draft',
                        'name': name and name.strip(),
                        'record_data': pprint.pformat(order_dict),
                        'shopify_config_id': shopify_config.id,
                    }
                    shop_queue_id.action_create_queue_lines(line_vals)
        return True

    def create_shopify_payment_gateway(self, gateway, shopify_config):
        """
            This Method create shopify payment gateway when queue of orders is created.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        gateway = gateway or 'blank_gateway'
        shopify_gateway = self.env['shopify.payment.gateway'].create({'name': gateway,
                                                                      'code': gateway,
                                                                      'shopify_config_id': shopify_config.id})

    def check_shopify_gateway(self, gateway, shopify_config):
        """
            This method checks whether payment gateway received in
            order data exists in the system or not in shopify payment
            gatewatys list.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        gateway = gateway or 'blank_gateway'
        shopify_gateway = self.env['shopify.payment.gateway'].sudo().search(
            [('code', '=', gateway), ('shopify_config_id', '=', shopify_config.id)], limit=1)
        return shopify_gateway or False

    def shopify_import_orders(self, shopify_config, from_date=False, to_date=False):
        """
           This method is used to create queue and queue line for orders.
           @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        shopify_config.check_connection()
        is_order_by_date_range = self.env.context.get(
            'is_order_by_date_range', False)
        from_order_date = from_date or shopify_config.last_import_order_date or fields.Datetime.now()
        to_order_date = to_date or fields.Datetime.now()
        shopify_order_list = self.fetch_all_shopify_orders(
            from_order_date, to_order_date, is_fetch_unfulfillment_order=shopify_config.is_fetch_unfulfillment_order)

        if shopify_order_list:
            payment_gateway = []
            for shopify_orders in tools.split_every(10, shopify_order_list):
                shop_queue_id = shopify_config.action_create_queue(
                    'import_order')
                for order in shopify_orders:
                    order_dict = order.to_dict()
                    name = order_dict.get('name', '')
                    line_vals = {
                        'shopify_id': order_dict.get('id') or '',
                        'state': 'draft',
                        'name': name and name.strip(),
                        'record_data': pprint.pformat(order_dict),
                        'shopify_config_id': shopify_config.id,
                    }
                    shop_queue_id.action_create_queue_lines(line_vals)
                    gateway = self.fetch_gateway_from_transaction(
                        order_dict.get('id'))
                    payment_gateway.append(gateway)
            # Code for checking shopify payment gateway and create if does not exist
            for gateway in list(set(payment_gateway)):
                if not self.check_shopify_gateway(gateway, shopify_config):
                    self.create_shopify_payment_gateway(
                        gateway, shopify_config)

        if not is_order_by_date_range:
            shopify_config.sudo().write(
                {'last_import_order_date': fields.Datetime.now()})
        return True

    def update_fulfilment_details_to_order(self, exist_order, shopify_config):
        """
            This method will update the fulfillment order details to order line.
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        shopify_order_id = exist_order.shopify_order_id
        order_line = exist_order.order_line.filtered(
            lambda line_item: line_item.shopify_fulfillment_line_id)
        if not order_line:
            shopify_order = shopify.Order().find(shopify_order_id)
            fulfillment_data = shopify_order.get('fulfillment_orders')
            for data in fulfillment_data:
                for line in data.get('line_items'):
                    order_line = exist_order.order_line.filtered(
                        lambda line_item: line_item.shopify_line_id == str(line.get('line_item_id')))
                    order_line.write(
                        {'shopify_fulfillment_order_id': line.get('fulfillment_order_id'),
                         'shopify_fulfillment_line_id': line.get('id')})
        return True

    def prepare_shopify_fulfillment_line_vals(self, picking_id, order_lines):
        """
            Using this method we are preparing fulfillment line vals for shopify.
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        line_items = []
        product_moves = picking_id.move_ids.filtered(
            lambda x: x.sale_line_id.product_id.id == x.product_id.id and x.state == "done")
        for move in product_moves.filtered(lambda line: line.product_id.detailed_type == 'product'):
            fulfillment_line_id = move.sale_line_id.shopify_fulfillment_line_id
            line_items.append({"id": fulfillment_line_id,
                               "quantity": int(move.product_qty)})
        return line_items

    def prepare_fulfillment_vals(self, sale_order, shopify_location_id, picking, line_items):
        """
            This method will prepare the fullfillment vals from orderlines.
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        tracking_info = {}
        shopify_order = shopify.Order().find(sale_order.shopify_order_id)
        fulfillment_orders = shopify_order.get('fulfillment_orders')
        if picking.carrier_id:
            tracking_info.update({"company": picking.carrier_id.name or ''})
        if picking.carrier_tracking_ref:
            tracking_info.update(
                {"number": picking.carrier_tracking_ref, "url": picking.carrier_tracking_url or ''})
        fulfillment_vals = {
            'location_id': shopify_location_id,
            "notify_customer": True,
            "line_items_by_fulfillment_order": [
                {
                    "fulfillment_order_id": fulfillment_orders[0].get('id'),
                    "fulfillment_order_line_items": line_items
                }]
        }
        if tracking_info:
            fulfillment_vals.update({"tracking_info": tracking_info})
        return fulfillment_vals

    def shopify_update_order_status(self, shopify_config, picking_ids=False):
        """
            This method will prepare the fullfillment order details
            to the shopify order and then create fullfillments at shopify.
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        shopify_config.check_connection()
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        if not shop_error_log_id:
            shop_error_log_id = error_log_env.sudo().create_update_log(
                shopify_config_id=shopify_config, operation_type='update_order_status')
        if not picking_ids:
            picking_ids = self.env['stock.picking'].search([
                ('shopify_config_id', '=', shopify_config.id),
                ('is_updated_in_shopify', '=', False),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'customer')], order='date')
        try:
            for picking in picking_ids:
                self.update_fulfilment_details_to_order(
                    picking.sale_id, shopify_config)
                carrier_name = picking.carrier_id or picking.carrier_id.name or ''
                sale_order = picking.sale_id
                order_lines = sale_order.order_line
                list_of_tracking_number = [
                    picking.carrier_tracking_ref] if picking.carrier_tracking_ref else []
                tracking_url = [picking.carrier_tracking_url or '']
                line_item_list = []
                shopify_location_id = picking.location_id.shopify_location_id
                line_item_dict = self.prepare_shopify_fulfillment_line_vals(
                    picking, order_lines)
                if shopify_location_id:
                    try:
                        fulfillment_vals = self.prepare_fulfillment_vals(
                            picking.sale_id, shopify_location_id, picking, line_item_dict)
                        new_fulfillment = shopify.fulfillment.FulfillmentV2(
                            fulfillment_vals)
                        fulfilment = new_fulfillment.save()
                        if fulfilment:
                            shopify_fullment_result = xml_to_dict(
                                new_fulfillment.to_xml())
                            shopify_fulfillment_id = ''
                            shopify_fulfillment_id = shopify_fullment_result.get(
                                'fulfillment').get('id') or ''
                            picking.write({'is_updated_in_shopify': True,
                                           'shopify_fulfillment_id': shopify_fulfillment_id,
                                           })
                    except Exception as e:
                        error_message = 'Failed to create fulfillment for Order : {}'.format(
                            e)
                        error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                               shopify_config_id=self.shopify_config_id,
                                                               operation_type='update_order_status',
                                                               shopify_log_line_dict={'error': [
                                                                   {'error_message': error_message,
                                                                    'queue_job_line_id': queue_line_id and queue_line_id.id or False, 'state': 'failed'}]})
                else:
                    raise ValidationError(
                        'Shipment is not associated with Shopify..!')
        except Exception as e:
            error_message = 'Failed to create fulfillment for Order : {}'.format(
                e)
            error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                   shopify_config_id=self.shopify_config_id,
                                                   operation_type='update_order_status',
                                                   shopify_log_line_dict={'error': [
                                                       {'error_message': error_message,
                                                        'queue_job_line_id': queue_line_id and queue_line_id.id or False, 'state': 'failed'}]})

    def shopify_import_returns_refunds(self, shopify_config, from_date=False, to_date=False):
        """This method is used to create queue and queue line for returns and refunds orders"""
        shopify_config.check_connection()
        order_type = self.env.context.get('order_type')
        from_order_date = from_date or shopify_config.last_import_order_date or fields.Datetime.now()
        to_order_date = to_date or fields.Datetime.now()
        shopify_order_list = self.fetch_all_shopify_orders(
            from_order_date, to_order_date)
        if shopify_order_list:
            for shopify_orders in tools.split_every(150, shopify_order_list):
                shop_queue_id = shopify_config.action_create_queue(order_type)
                for order in shopify_orders:
                    order_dict = order.to_dict()
                    name = order_dict.get('name', '')
                    line_vals = {
                        'shopify_id': order_dict.get('id') or '',
                        'state': 'draft',
                        'name': name and name.strip(),
                        'record_data': pprint.pformat(order_dict),
                        'shopify_config_id': shopify_config.id,
                    }
                    shop_queue_id.action_create_queue_lines(line_vals)
        else:
            raise UserError(
                "Please enabled Is Import order by date range boolean then proceed for import returns/refunds operations .")
        return True


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    shopify_line_id = fields.Char(string='Shopify Line ID', copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        copy=False)
    shopify_price_unit = fields.Float(string='Shopify Unit Price', copy=False)
    shopify_discount_amount = fields.Float(
        string='Shopify Discount Total', copy=False)
    shopify_fulfillment_line_id = fields.Char(
        "Fulfillment Line ID", copy=False)
    shopify_fulfillment_order_id = fields.Char(
        "Fulfillment Order ID", copy=False)


class SaleDownpaymentHistory(models.Model):
    _name = 'sale.downpayment.history'
    _description = 'Sale Downpayment History'

    sale_id = fields.Many2one('sale.order', string="Order", copy=False)
    amount = fields.Float(string="Amount")
    invoice_id = fields.Many2one('account.move', string="Invoice")
