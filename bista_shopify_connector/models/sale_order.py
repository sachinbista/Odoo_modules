##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from .. import shopify
import time
import pytz
from datetime import datetime, timedelta
from dateutil import parser
import urllib.parse as urlparse
from odoo import fields, models, tools, _, api, registry
from odoo.exceptions import AccessError, ValidationError, UserError
from pyactiveresource.util import xml_to_dict
import requests
import logging

utc = pytz.utc

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def update_order_status(self):
        for order in self:
            if order.shopify_config_id:
                pickings = order.picking_ids.filtered(
                    lambda x: x.state != "cancel")
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
    shopify_payment_gateway_ids = fields.Many2many(
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
    shopify_source_name = fields.Char(string="Shopify Source Name")

    def cancel_shopify_delivery_orders(self):
        for each_order in self.picking_ids.filtered(lambda x: x.state == 'done'):
            return_location_id = self.env['stock.location'].search([('return_location', '=', True), ('company_id', '=', each_order.company_id.id)])
            val_list = {'location_id': return_location_id.id if return_location_id else each_order.location_id.id,
                        'picking_id': each_order.id}
            return_wizard_id = (self.env['stock.return.picking'].with_context(active_model='stock.picking', active_ids=each_order.ids)
                                .create(val_list))
            return_wizard_id._compute_moves_locations()
            new_return_picking_id = return_wizard_id.create_returns()
            new_return_picking_id = self.env['stock.picking'].browse(new_return_picking_id.get('res_id', False))
            new_return_picking_id.with_context(skip_sms=True, shopify_picking_validate=True).button_validate()
            return True

    def action_cancel(self):
        if self.shopify_order_id:
            if self._context.get('yes'):
                shopify_log_line_obj = self.env['shopify.log.line']
                log_line_vals = {
                    'name': "Cancel sale order in shopify form odoo",
                    'shopify_config_id': self.shopify_config_id.id,
                    # 'operation_type': 'import_order',
                }
                parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                try:
                    job_descr = _("Cancel Sale Order In Shopify From Odoo:   %s") % (
                            self.name and self.name.strip())
                    log_line_id = shopify_log_line_obj.create({
                        'name': job_descr,
                        'shopify_config_id': self.shopify_config_id.id,
                        'id_shopify': self.id,
                        # 'operation_type': 'import_order',
                        'parent_id': parent_log_line_id.id
                    })
                    self.with_company(self.shopify_config_id.default_company_id).with_delay(
                        description=job_descr, max_retries=5).cancel_shopify_sale_order(
                        self.shopify_config_id)
                    _logger.info("Started Process Of Cancelling sale order->:")
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
                self.cancel_shopify_delivery_orders()
                return super(SaleOrder, self).action_cancel()
            if self._context.get('no') or self._context.get('cancel'):
                self.cancel_shopify_delivery_orders()
                return super(SaleOrder, self).action_cancel()
            return {
                'type': 'ir.actions.act_window',
                'name': _('Cancel Sale Order in Shopify'),
                'res_model': 'cancel.shopify.order',
                'view_mode': 'form',
                'view_id': self.env.ref('bista_shopify_connector.view_sale_order_form_name').id,
                'target': 'new',
                'context': {
                    'default_order_id': self.id,
                }
            }

        else:
            return super(SaleOrder, self).action_cancel()

    def cancel_shopify_sale_order(self, shopify_config):
        order_id = self.shopify_order_id
        base_url = shopify_config.shop_url
        api_order_url = ("/admin/api/2021-07/orders/%s/cancel.json") % (order_id)
        url = base_url + api_order_url
        headers = {'X-Shopify-Access-Token': shopify_config.password}

        try:
            response = requests.request('POST', url=url, headers=headers,
                                        )
        except Exception as e:
            error_message = 'Error in updating order status : {}'.format(
                e)
            raise ValidationError(_(error_message))

    def create_update_sale_order_from_webhook(self, res, shopify_config):
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "WebHook Create/Update Sales Order",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_order',
        }
        user = self.env.ref('base.user_root')
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            shopify_config.check_connection()
            name = res.get('name', '')
            job_descr = _("WebHook Create/Update Sales Order:   %s") % (
                    name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': res.get('id') or '',
                'operation_type': 'import_order',
                'parent_id': parent_log_line_id.id
            })
            self.env["sale.order"].with_user(user).with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5).create_update_shopify_orders(
                    res, shopify_config, log_line_id)
            _logger.info("Started Process Of Creating Orders Via Webhook->:")
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


    def shopify_odoo_webhook_for_order_update(self, res, shopify_config):
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "WebHook Create/Update Sales Order",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_order',
        }
        user = self.env.ref('base.user_root')
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        try:
            shopify_config.check_connection()
            name = res.get('name', '')
            job_descr = _("WebHook Create/Update Sales Order:   %s") % (
                    name and name.strip())
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': res.get('id') or '',
                'operation_type': 'import_order',
                'parent_id': parent_log_line_id.id
            })
            self.env["sale.order"].with_user(user).with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5).create_update_shopify_orders(
                    res, shopify_config, log_line_id)
            _logger.info("Started Process Of Updating Orders Via Webhook->:")
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



    @api.depends('downpayment_history_ids', 'downpayment_history_ids.amount')
    def get_remaining_downpayment(self):
        for order in self:
            order.remaining_downpayment = sum(
                order.downpayment_history_ids.mapped('amount'))

    def manual_create_downpayment_invoice(self, movetype, amount):
        dpname = _('Down Payment')
        sale_adv_pay_inv_obj = self.env['sale.advance.payment.inv']
        dp_product_id = sale_adv_pay_inv_obj._default_product_id()
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
        self.env['sale.downpayment.history'].sudo().create({'sale_id': self.id,
                                                            'amount': invoice.amount_total_signed,
                                                            'invoice_id': invoice.id})
        return invoice

    @api.depends('order_line.invoice_lines')
    def _get_invoiced(self):
        """
            Using this method linked the count of invoices which is as Shopify credeit and
            in odoo created as the invoice for refund order of Shopify note
            that is move_type has out_refund.
        """
        super_data = super(SaleOrder, self)._get_invoiced()
        for order in self:
            domain = [('move_type', '=', 'out_refund'),
                      ('sale_order_id', '=', order.id),
                      ('shopify_order_id', '=', order.shopify_order_id)]
            invoices = order.mapped('invoice_ids')
            if invoices:
                domain += [('id', 'not in', invoices.ids)]
            refund_invoices = self.env['account.move'].search(domain)
            invoices += refund_invoices
            order.invoice_count = len(invoices)

    # link shopify credit note with order
    def action_view_invoice(self, invoices=False):
        super_data = super(SaleOrder, self).action_view_invoice(invoices=invoices)
        for sale in self:
            if sale.shopify_order_id:
                refund_invoices = self.env['account.move'].search(
                    [('move_type', '=', 'out_refund'),
                     ('sale_order_id', '=', sale.id),
                     ('shopify_order_id', '=', sale.shopify_order_id)])
                if refund_invoices:
                    action = self.sudo().env.ref(
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
        invoices = self.downpayment_history_ids.mapped('invoice_id')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        refund_invoices = self.env['account.move'].search(
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
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or
                                                   self.env['account.move'].default_get(
                                                       ['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
                'default_user_id': self.user_id.id,
            })
        action['context'] = context
        return action

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        if self.picking_ids:
            [picking.write({'shopify_config_id': self.shopify_config_id.id,
                            'shopify_order_id': self.shopify_order_id,
                            }) for picking in self.picking_ids]
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for each in self:
            picking_ids = each.picking_ids.filtered(
                lambda s: not s.shopify_config_id and s.shopify_order_id)
            if picking_ids:
                [picking.write({'shopify_config_id': each.shopify_config_id.id,
                                'shopify_order_id': each.shopify_order_id,
                                }) for picking in picking_ids]
        return res

    def get_customer(self, shopify_customer_id, shopify_config, customer_data):
        """ This method returns existing shopify customer or creates new customer based on customer data in sales order """
        Partner = self.env['res.partner']
        partner_id = Partner.search([('shopify_customer_id', '=', str(
            shopify_customer_id)), ('shopify_config_id', '=', shopify_config.id)], limit=1)
        if not partner_id:
            if shopify_config.is_create_customer == True:
                Partner.shopify_import_customer_by_ids(
                    shopify_config, shopify_customer_by_ids=shopify_customer_id)
                # Partner.create_update_shopify_customers_temp(customer_data, shopify_config)
                partner_id = Partner.search([('shopify_customer_id', '=', str(
                    shopify_customer_id)), ('shopify_config_id', '=', shopify_config.id)], limit=1)
        return partner_id or False

    def get_product(self, shopify_variant_id, shopify_product_id, shopify_config, sku, barcode):
        """ This method will search variant in shopify product product mapping and return odoo product from there.
            If variant id not found in shopify product product mapping, product API with ID will be called and
            new mapping will be created and then product will be returned from that new mapping
        """
        # shopify_product_obj = self.env['shopify.product.template']
        # odoo_product = shopify_product_obj.odoo_product_search_sync(
        #     shopify_config, sku, barcode)
        # if odoo_product:
        #     return odoo_product
        ShopifyProductProduct = self.env['shopify.product.product']
        shopify_product_product_id = ShopifyProductProduct.sudo().search(
            [('shopify_product_id', '=', shopify_variant_id)], limit=1)
        # Code for creating new product in odoo if product not found while importing orders
        # if not shopify_product_product_id:
        #     ShopifyProductTemplate = self.env['shopify.product.template']
        #     ShopifyProductTemplate.shopify_import_product_by_ids(shopify_config, shopify_product_by_ids=str(shopify_product_id))
        #     shopify_product_product_id = ShopifyProductProduct.search([('shopify_product_id', '=', shopify_variant_id)], limit=1)
        return (shopify_product_product_id and
                shopify_product_product_id.product_variant_id or False)

    def get_shopify_custom_product(self, custom_product_name):
        ShopifyProductMapping = self.env['shopify.product.mapping']
        shopify_product_mapping_id = ShopifyProductMapping.sudo().search(
            [('shopiy_product_name', '=', custom_product_name)], limit=1)
        if shopify_product_mapping_id:
            return shopify_product_mapping_id.product_variant_id
        else:
            return False

    def create_shipping_or_billing_address(self, vals, parent_id=False,
                                           atype=''):
        country_obj = self.env['res.country']
        state_obj = self.env['res.country.state']
        partner_obj = self.env['res.partner']
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

        address = self.env['res.partner'].search([
            ('name', '=', name), ('state_id', '=', state.id),
            ('city', '=', city), ('zip', '=', zip), ('street', '=', street),
            ('street2', '=', street1),
            ('parent_id', '=', parent_id),
            ('country_id', '=', country.id)], limit=1)
        if not address:
            address = self.env['res.partner'].create({
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

    def get_financial_workflow(self, shopify_config, shopify_payment_gateway, shopify_financial_status,workflow,
                               shopify_payment_term=False):
        # TODO: Check if payment term to be used or not for searching financial workflow
        # TODO: Add company id domain in search and company id field in workflow
        # TODO: Add constraint on financial workflow to have only 1 combination of payment_gateway and financial status
        # FinancialWorkflow = self.env['shopify.financial.workflow']
        # financial_workflow_id = FinancialWorkflow.search([('shopify_config_id', '=', shopify_config.id),
        #                                                   ('payment_gateway_id', '=', shopify_payment_gateway.id),
        #                                                   ('financial_status', '=', shopify_financial_status)
        #                                                   # ('payment_term_id', '=', shopify_payment_term),
        #                                                 ], limit=1)
        financial_workflow_id = shopify_config.financial_workflow_ids.filtered(
            lambda
                r: r.payment_gateway_id.id == shopify_payment_gateway.id and r.financial_status == shopify_financial_status and r.auto_workflow_id.id == workflow.id)

        return financial_workflow_id and financial_workflow_id[0] or False

    def prepare_workflow_vals(self, order_dict, shopify_config):
        gateway = order_dict.get('gateway') if order_dict.get(
            'gateway') else order_dict.get('payment_gateway_names') and \
                            order_dict.get('payment_gateway_names')
        shopify_payment_gateway_ids = []
        for each in gateway:
            shopify_payment_gateway_id = self.check_shopify_gateway(
                each, shopify_config)
            if shopify_payment_gateway_id:
                shopify_payment_gateway_ids.append(shopify_payment_gateway_id)
        list_shopify_payment_gateway_ids = [rec.id if shopify_payment_gateway_ids else False for rec in  shopify_payment_gateway_ids]
        shopify_financial_status = order_dict.get('financial_status')
        workflow = self.env['shopify.workflow.process'].search([('company_id', '=', shopify_config.default_company_id.id)])
        if shopify_payment_gateway_ids and shopify_financial_status:
            for wf in workflow:
                financial_workflow_id = self.get_financial_workflow(
                    shopify_config, shopify_payment_gateway_ids[0], shopify_financial_status, wf)
                if financial_workflow_id:
                    return {'financial_workflow_id': financial_workflow_id.id,
                            'shopify_payment_gateway_ids': list_shopify_payment_gateway_ids,
                            'auto_workflow_id': financial_workflow_id.auto_workflow_id.id,
                            'payment_term_id': financial_workflow_id.payment_term_id.id
                            }

            sales_journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', shopify_config.default_company_id.id)],
                limit=1)
            if sales_journal:
                workflow = self.env['shopify.workflow.process'].create({
                    'name': str(datetime.now()) + ' Automatic',
                    'confirm_order': True,
                    'create_invoice': True,
                    'validate_invoice': True,
                    'register_payment': True,
                    'company_id': shopify_config.default_company_id.id,
                    'sale_journal_id': sales_journal.id,
                    'credit_note_journal_id': sales_journal.id,
                    'shipping_policy': 'one',
                })
            workflow_data = {
                'shopify_config_id': shopify_config.id,
                'payment_gateway_id': shopify_payment_gateway_ids[0].id,
                'auto_workflow_id': workflow[0].id,
                'financial_status': shopify_financial_status,
                'payment_term_id': shopify_config.default_payment_term_id.id,
            }
            new_financial_workflow_id = shopify_config.financial_workflow_ids.create(workflow_data)
            return {'financial_workflow_id': new_financial_workflow_id.id,
                    'shopify_payment_gateway_ids': list_shopify_payment_gateway_ids,
                    'auto_workflow_id': workflow[0].id,
                    'payment_term_id': shopify_config.default_payment_term_id.id
                    }

    def prepare_order_vals(self, partner_id, billing_addr_id, shipping_addr_id, order_dict, shopify_config):
            shopify_order_id = order_dict.get('id')
            shopify_order_name = order_dict.get('name')
            shopify_note = order_dict.get('note')
            shopify_order_date = order_dict.get('created_at')
            order_date = self.convert_date_utc(shopify_order_date)
            shopify_tags = order_dict.get('tags')
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
                          }
            if shopify_tags:
                tag_ids = self.create_shopify_order_tags_in_odoo(shopify_tags)
                if tag_ids:
                    order_vals.update({'shopify_tag_ids': [(6, 0, tag_ids.ids)]})
            return order_vals

    def create_shopify_order_tags_in_odoo(self, shopify_tags):
        shopify_tags_obj = self.env['shopify.tags']
        shop_tags_obj = self.env['shopify.tags']
        tag_list = list(shopify_tags.split(","))
        list_tags = []
        for tag in tag_list:
            updated_tag = tag.strip()
            if updated_tag:
                tag_id = shopify_tags_obj.search([('name', '=', updated_tag)])
                if not tag_id:
                    tag_id = shopify_tags_obj.create({'name': tag.strip()})
                shop_tags_obj |= tag_id
        # tag_ids = shopify_tags_obj.browse(list_tags)
        return shop_tags_obj

    def shopify_create_tax(self, tax_line, taxes_included, shopify_config):
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
                             'company_id': shopify_config.default_company_id.id})
        tax_id.mapped("invoice_repartition_line_ids").write(
            {"account_id": shopify_config.default_tax_account_id and shopify_config.default_tax_account_id.id or False})
        tax_id.mapped("refund_repartition_line_ids").write(
            {
                "account_id": shopify_config.default_tax_cn_account_id.id and shopify_config.default_tax_cn_account_id.id or False})
        return tax_id

    def get_tax_ids(self, shopify_tax_lines, taxes_included, shopify_config):
        # shopify_tax_lines = shopify_line['tax_lines']
        taxes = []
        for line in shopify_tax_lines:
            rate = float(line.get('rate', 0.0)) * 100
            title = line.get('title')
            price = float(line.get('price'))
            rate_calc = round(rate, 4)
            name = "%s%s%s" % (title, rate_calc, '%')
            if price != 0.0:
                tax_id = self.env["account.tax"].search([('price_include', '=', taxes_included),
                                                         ('amount', '=', rate_calc),
                                                         ('name', '=', name),
                                                         ('type_tax_use',"=", 'sale'),
                                                         ('company_id', '=', shopify_config.default_company_id.id)],
                                                        limit=1)
                if not tax_id:
                    tax_id = self.shopify_create_tax(
                        line, taxes_included, shopify_config)
                if tax_id:
                    taxes.append(tax_id.id)
        return taxes

    def get_carrier(self, code, title, shopify_config):
        # TODO: Check for 'source' parameter in payload and if required add that in search and create method of shipping method
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
        """Return carrier information based on carrier name in case not
        found Odoo will create new based on name."""
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

    def fetch_order_fulfillment_location_from_shopify(self, shopify_order_dict):
        # This method set location in the Shopify order line dict.
        fulfillments = shopify.FulfillmentOrders.find(order_id=shopify_order_dict.get('id'))
        fulfillment_list = [fulfillment.to_dict() for fulfillment in fulfillments]
        if fulfillment_list:
            for fulfillment_dict in fulfillment_list:
                for line_item in fulfillment_dict.get('line_items'):
                    [shopify_order_line_item.update({'location_id': fulfillment_dict.get('assigned_location_id')})
                     for shopify_order_line_item in shopify_order_dict.get('line_items', []) if
                     shopify_order_line_item.get('id') == line_item.get('line_item_id')]
        return shopify_order_dict

    def update_fulfilment_details_to_order(self, exist_order, shopify_config):
        shopify_order_id = exist_order.shopify_order_id
        order_line = exist_order.order_line.filtered(lambda line_item: line_item.shopify_fulfillment_line_id)
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

    def prepare_order_line_vals(self, shopify_line, product_id,
                                taxes_included, shopify_config,
                                shopify_line_id, fulfill_line):
        shopify_variant_id = shopify_line.get('variant_id')
        shopify_product_id = shopify_line.get('product_id')
        qty = fulfill_line[3]
        price_unit = shopify_line.get('price') and float(shopify_line['price'])
        shopify_tax_lines = shopify_line['tax_lines']
        discount_lines = shopify_line.get('discount_allocations', False)
        location_id = shopify_line.get('location_id')
        # shopify_product_product_id = self.get_product(shopify_variant_id, shopify_product_id, shopify_config)
        # product_id = shopify_product_product_id.product_variant_id

        order_line_dict = {
            'shopify_line_id': shopify_line_id,
            'shopify_config_id': shopify_config.id,
            'name': product_id.name,
            'product_id': product_id.id,
            'product_uom_qty': qty,
            'product_uom': product_id.uom_id and product_id.uom_id.id or False,
            'price_unit': price_unit,
            'shopify_price_unit': price_unit,
            'shopify_location_id': location_id if location_id else False,
            'assigned_location_id': fulfill_line[0],
            'shopify_fulfillment_order_id': fulfill_line[1],
            'shopify_fulfillment_line_id': fulfill_line[2]
        }
        # TODO: Tax based on fiscal position defined in odoo
        tax_ids = self.get_tax_ids(
            shopify_tax_lines, taxes_included, shopify_config)
        if tax_ids:
            order_line_dict.update({'tax_id': [(6, 0, tax_ids)]})
        if discount_lines:
            discount_amount_total = self.get_discount_amount(discount_lines)
            if qty != 0:
                price_unit -= (discount_amount_total / qty)
            if price_unit < 0.0:
                price_unit = 0.0
            order_line_dict.update({
                'price_unit': price_unit,
                'shopify_discount_amount': discount_amount_total
            })
            # order_line_dict['price_unit'] = price_unit
        return order_line_dict, tax_ids

    def get_discount_amount(self, discount_lines):
        discount_amount = 0.0
        for discount_line in discount_lines:
            discount_amount += float(discount_line.get('amount', 0.0))
        return discount_amount

    # def prepare_discount_line_vals(self, product_id, discount_lines, tax_ids, shopify_config):
    #     discount_product_id = shopify_config.disc_product_id
    #     if not discount_product_id:
    #         raise UserError(_("Discount Product not configured."))
    #     discount_amount = 0.0
    #     # discount_lines = line.get('discount_allocations')
    #     for discount_line in discount_lines:
    #         discount_amount += float(discount_line.get('amount', 0.0))
    #     name = "Discount for product %s" % product_id.name
    #     discount_line_dict = {}
    #     if discount_amount > 0:
    #         discount_line_dict = {'name': name,
    #                               'product_id': discount_product_id.id,
    #                               'product_uom_qty': 1,
    #                               'product_uom': discount_product_id.uom_id and discount_product_id.uom_id.id or False,
    #                               'price_unit': discount_amount * -1,
    #                               'tax_id': tax_ids,
    #                             }
    #     return discount_line_dict

    # def check_rounding_diff(self, order_id, shopify_total_amount, shop_error_log_id, queue_line_id):
    #     """
    #     This method will check rounding diff of odoo order total amount and shopify total amount.
    #     If rounding diff in [-0.01,-0.02,0.01,0.02] then add sale order line and create error log
    #     If rounding diff not in about list, then import order and create error log
    #     """
    #     precision_price = self.env['decimal.precision'].precision_get('Product Price')
    #     product_id = self.env.ref('bista_shopify_connector.shopify_rounding_diff_product')
    #     order_total_amount = order_id.amount_total
    #     diff = float_round((order_total_amount - shopify_total_amount), precision_digits=precision_price)
    #     SaleOrderLine = self.env['sale.order.line']
    #     rounding_diff_desc = "Shopify Order rounding difference"
    #     if diff != 0:
    #         if not product_id:
    #             raise UserError(_("Rounding Difference product not found"))
    #         if diff in [-0.01, -0.02, 0.01, 0.02]:
    #             line_vals_dict = {
    #                                 'product_id': product_id.id,
    #                                 'name': rounding_diff_desc,
    #                                 'price_unit': abs(diff),
    #                                 'product_uom_qty': diff > 0 and -1 or 1,
    #                                 'product_uom': product_id.uom_id.id,
    #                                 'order_id': order_id.id
    #                              }
    #             order_line_id = SaleOrderLine.create(line_vals_dict)
    #         order_id.has_rounding_diff = True
    #         error_log_env.create_update_log(
    #                 shop_error_log_id=shop_error_log_id,
    #                 shopify_log_line_dict={'error': [
    #                     {'error_message': "Order %s has rounding diff" % order_id.shopify_order_id,
    #                      'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})

    def prepare_shipping_line_vals(self, shipping_line, taxes_included, shopify_config):
        shipping_product_id = shopify_config.shipping_product_id
        if not shipping_product_id:
            raise UserError(_("Discount Product not configured."))
        shipping_price = float(shipping_line.get('price', 0.0))
        discount_lines = shipping_line.get('discount_allocations', False)
        shipping_line_dict = {'name': shipping_product_id.name,
                              'product_id': shipping_product_id.id,
                              'product_uom_qty': 1,
                              'product_uom': shipping_product_id.uom_id and shipping_product_id.uom_id.id or False,
                              'price_unit': shipping_price,
                               'is_delivery': True,
                              'shopify_shipping_line': True
                              }

        if discount_lines:
            discount_amount_total = self.get_discount_amount(discount_lines)
            shipping_price = shipping_price - discount_amount_total
            shipping_line_dict.update({
                'price_unit': shipping_price,
                'shopify_discount_amount': discount_amount_total
            })

        shipping_tax_lines = shipping_line.get('tax_lines')
        tax_ids = self.get_tax_ids(
            shipping_tax_lines, taxes_included, shopify_config)
        if tax_ids:
            shipping_line_dict.update({'tax_id': [(6, 0, tax_ids)]})
        return shipping_line_dict

    def get_shopify_location(self, shopify_location_id, shopify_config):
        # Commented this code because of new mapping table of location
        # location_id = self.env['stock.location'].search([('shopify_location_id', '=', shopify_location_id),
        #                                                  ('shopify_config_id',
        #                                                   '=', shopify_config.id),
        #                                                  ('usage', '=', 'internal')
        #                                                  ], limit=1)
        mapping_location_id = self.env['shopify.location.mapping'].search(
            [('shopify_location_id', '=', shopify_location_id),
             ('shopify_config_id',
              '=', shopify_config.id)
             ], limit=1)
        return mapping_location_id.odoo_location_id.id or False

    def get_shopify_warehouse_location(self, order_dict, shopify_config):
        """
        TODO: ISSUE TO FIX > if default wh (shopify config) set on order and stock not available for few products,
        on confirming the order, picking will be created for products that are available in that wh.
        """
        shopify_location_id = False
        warehouse_id = False
        if order_dict.get('location_id'):
            shopify_location_id = order_dict.get('location_id')
        elif order_dict.get("fulfillments") and order_dict.get(
                "fulfillments")[0].get('location_id'):
            shopify_location_id = order_dict.get(
                "fulfillments")[0].get('location_id')
        elif order_dict.get("line_items") and (order_dict.get(
                "line_items")[0].get('location_id') or order_dict.get(
            "line_items")[0].get('assigned_location_id')):
            shopify_location_id = order_dict.get(
                "line_items")[0].get('location_id') or order_dict.get(
                "line_items")[0].get('assigned_location_id')

        location_mapping_id = self.env['shopify.location.mapping'].search([
            ('shopify_location_id', '=', shopify_location_id),
            ('shopify_config_id', '=', shopify_config.id),
            ('odoo_location_id', '!=', False)], limit=1)
        if location_mapping_id and location_mapping_id.warehouse_id:
            warehouse_id = location_mapping_id.warehouse_id
        if not warehouse_id:
            warehouse_id = self.env['stock.warehouse'].search(
                [('shopify_config_id', '=', shopify_config.id)], limit=1)
            if not warehouse_id:
                warehouse_id = shopify_config.warehouse_id
        return {'location_id': location_mapping_id.odoo_location_id or shopify_config.warehouse_id.lot_stock_id,
                'warehouse_id': warehouse_id}

    def process_picking_for_kit_products(self, picking_id, move_ids, qty_done, product_id):
        return

    def process_picking(self, picking_id, fulfilment_line, shopify_config):
        # Avoid updating inv in shopify at the time of import order and process DO
        updated_qty_sm_id = []
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
                product_id = shopify_product_product_id or False
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
            move_ids = picking_id.move_ids_without_package.filtered(lambda r: r.product_id.id == product_id.id)
            picking_id.action_assign()
            for move in move_ids:
                update_qty = 0.00
                if move.quantity and qty_done <= move.quantity:
                    update_qty = qty_done
                elif move.quantity > 0:
                    update_qty = move.quantity
                if update_qty > 0:
                    move.quantity = update_qty
                    if qty_done > move.quantity:
                        raise UserError(_("Please update quantity of '%s' on '%s' to process the order '%s'!") %
                                        (
                                        product_id.name, picking_id.location_id.complete_name, picking_id.sale_id.name))
                    else:
                        updated_qty_sm_id.append(move.id)
                else:
                    raise UserError(_("Please update quantity of '%s' on '%s' to process the order '%s'!") %
                                    (product_id.name, picking_id.location_id.complete_name, picking_id.sale_id.name))
            if updated_qty_sm_id:
                unfullfilled_product = picking_id.move_ids_without_package.filtered(lambda r: r.id not in updated_qty_sm_id)
                if unfullfilled_product:
                    unfullfilled_product.write({'quantity': 0})
            self.process_picking_for_kit_products(picking_id, move_ids, qty_done, product_id)
        carrier_id = self.check_carrier(fulfilment_line.get(
            'tracking_company'), fulfilment_line.get('service'))
        picking_id.carrier_id = carrier_id and carrier_id.id or None
        # picking_id.action_assign()
        picking_validate = picking_id.with_context(
            skip_sms=True, shopify_picking_validate=True).button_validate()
        if isinstance(picking_validate, dict):
            if picking_validate.get('res_model') == 'stock.backorder.confirmation':
                ctx = picking_validate.get('context')
                backorder_id = self.env['stock.backorder.confirmation'].with_context(
                    ctx).create({'pick_ids': [(4, picking_id.id)]})
                backorder_id.process()
        picking_id.write(
            {'shopify_fulfillment_id': fulfilment_line.get('id') and str(fulfilment_line.get('id')) or None,
             'shopify_order_id': self._context.get('shopify_order_id', None),
             'shopify_fulfillment_service': fulfilment_line.get('service'),
             'shopify_config_id': shopify_config.id,
             'carrier_tracking_ref': fulfilment_line.get('tracking_number'),
             'is_updated_in_shopify': True,
             })

    def process_fullfilled_orders(self, shopify_fulfilment_lines, shopify_config):
        for line in shopify_fulfilment_lines:
            if line.get('status') == 'success':
                fulfilled_picking_id = self.picking_ids.filtered(
                    lambda r: r.shopify_fulfillment_id == str(line.get('id')))
                if fulfilled_picking_id:
                    continue
                shopify_location_id = line.get(
                    'location_id') and str(line.get('location_id'))
                create_dt = line.get('created_at')
                location_mapping_id = self.env['shopify.location.mapping'].search([
                    ('shopify_location_id', '=', shopify_location_id)])
                picking_id = self.picking_ids.filtered(lambda r: r.state not in [
                    'cancel', 'done'] and r.location_id == location_mapping_id.odoo_location_id)
                if picking_id:
                    self.process_picking(picking_id, line, shopify_config)
                else:
                    picking_id = self.picking_ids.filtered(
                        lambda r: r.state not in ['cancel', 'done'] and not r.shopify_fulfillment_id)
                    if picking_id:
                        # TODO: Fix for updating operation type in picking for correct locationn
                        # picking_id.picking_type_id = self.get_shopify_location(shopify_location_id, shopify_config)
                        # picking_id.onchange_picking_type()
                        # picking_id.move_line_ids_without_package.unlink()
                        picking_id.location_id = self.get_shopify_location(
                            shopify_location_id, shopify_config)
                        self.process_picking(picking_id, line, shopify_config)
        return True

    def process_shopify_order_fullfillment(self, shopify_config, fulfillment_status=False, fulfillment_lines=[]):
        """
        Check state of order and confirm it to create delivery order if required.
        Process delivery order in odoo based on fulfilment data received.
        """
        if self.state not in ["sale", "done", "cancel"]:
            self.action_confirm()
        if fulfillment_status in ['partial', 'fulfilled'] and fulfillment_lines:
            self.process_fullfilled_orders(fulfillment_lines, shopify_config)
        # TODO: Method call for processing delivery order
        return True

    def prepare_return_picking_vals(self, shopify_config, order_id, picking_id, shopify_refund_id):
        picking_type_id = picking_id.picking_type_id.return_picking_type_id
        location_dest_id = self.env['stock.location'].search([
            ('is_shopify_return_location', '=', True),
            ('shopify_config_id', '=', shopify_config.id)], limit=1)
        if not location_dest_id:
            location_dest_id = picking_id.location_id
        if not picking_type_id:
            picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', order_id.warehouse_id.id),
                ('company_id', '=', order_id.company_id.id)], limit=1)
        vals = {
            'partner_id': order_id.partner_id.id,
            'picking_type_id': picking_type_id.id,
            'origin': order_id.name,
            'group_id': picking_id.group_id.id,
            'company_id': picking_id.company_id.id,
            'shopify_order_id': picking_id.shopify_order_id,
            'shopify_refund_id': shopify_refund_id,
            'location_dest_id': location_dest_id.id,
            'location_id': picking_id.location_dest_id.id,
        }
        return vals

    def create_return_picking_move(self, refund_line, return_picking_id, procurement_group_id):
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
        else:
            raise UserError(
                _("Order Line not found for shopify line id %s." % line_item_id))

    def create_return_pickings(self, shopify_config, order_id, refund_data):
        StockPicking = self.env['stock.picking']
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
                    refund_line_items = refund_line.get('refund_line_items')
                    return_move_ids = []
                    new_return_picking_id = StockPicking
                    for line in refund_line_items:
                        # TODO: Check for return reason to be stored at picking level
                        # don't added picking line if product type is service
                        line_item_id = line.get('line_item_id')
                        order_line_id = self.env['sale.order.line'].search(
                            [('shopify_line_id', '=', line_item_id)], limit=1)
                        if (line.get('restock_type') != 'return') or (
                                order_line_id and order_line_id.product_id.type == 'service'):
                            if line.get('restock_type') == 'cancel':
                                # Bhaviraj
                                # commented due to direct adjustments to order.
                                # picking_id.action_cancel()
                                continue
                        if not new_return_picking_id:
                            new_return_picking_id |= StockPicking.create(
                                return_picking_vals)
                        self.create_return_picking_move(
                            line, new_return_picking_id, picking_id.group_id)
                    if new_return_picking_id:
                        new_return_picking_id.action_confirm()
                        used_move_ids = []
                        for move in (
                                new_return_picking_id.move_ids_without_package.filtered(
                                    lambda m: m.product_id.tracking != 'none')):
                            if move.move_line_ids:
                                for line in move.move_line_ids:
                                    if move.product_id.tracking == "serial":
                                        move_line_id = (
                                            order_id.picking_ids.filtered(
                                                lambda x: x.picking_type_id.code == 'outgoing').mapped(
                                                'move_ids_without_package').filtered(
                                                lambda m: m.product_id.id ==
                                                          move.product_id.id).move_line_ids.filtered(
                                                lambda l: l.id not in
                                                          used_move_ids and l.lot_id.product_qty == 0)[0])
                                        if move_line_id:
                                            line.lot_id = (move_line_id.lot_id and
                                                           move_line_id.lot_id.id
                                                           or False)
                                            used_move_ids.append(move_line_id.id)
                                    else:
                                        new_return_picking_moves_ids = move.move_line_ids
                                        new_return_sml_id_copy = new_return_picking_moves_ids[0].copy()
                                        new_return_picking_moves_ids.unlink()
                                        return_move_qty = move.product_uom_qty
                                        return_done_qty = 0.0
                                        tmp_return_move_qty = return_move_qty
                                        outgoing_sml = (order_id.picking_ids.filtered(
                                            lambda x: x.picking_type_id.code == 'outgoing').mapped(
                                            'move_ids_without_package').filtered(
                                            lambda m: m.product_id.id ==
                                                      move.product_id.id).move_line_ids)
                                        while return_move_qty != return_done_qty:
                                            for each in outgoing_sml:
                                                avail_lot_qty = each.quantity
                                                if avail_lot_qty >= tmp_return_move_qty:
                                                    new_return_sml_id_copy.copy({'lot_id': each.lot_id.id,
                                                                                 'quantity': tmp_return_move_qty})
                                                    return_done_qty += tmp_return_move_qty
                                                    tmp_return_move_qty -= tmp_return_move_qty
                                                elif avail_lot_qty < tmp_return_move_qty:
                                                    new_return_sml_id_copy.copy({'lot_id': each.lot_id.id,
                                                                                 'quantity': avail_lot_qty})
                                                    return_done_qty += avail_lot_qty
                                                    tmp_return_move_qty -= avail_lot_qty
                                        new_return_sml_id_copy.unlink()
                        new_return_picking_id.with_context(
                            skip_sms=True, shopify_picking_validate=True).button_validate()

    def create_shopify_credit_note_in_odoo(self, invoice_id):
        """
        This method will use to create shopify order credit note for fully invoice.
        """
        invoice = invoice_id.filtered(
            lambda l: l.state != 'cancel' and not l.is_downpayment_inv and l.move_type == 'out_invoice')
        if self.downpayment_history_ids:
            invoice_id = self.downpayment_history_ids.mapped('invoice_id')
            invoice = invoice_id.filtered(
                lambda l: l.state != 'cancel' and l.move_type == 'out_invoice')
        if not invoice:
            return False

        get_refunds = shopify.Refund.find(order_id=str(self.shopify_order_id))
        for refunds in get_refunds:
            refund_dict = refunds.attributes
            order_id = str(refund_dict.get('order_id'))

            # shopify_transactions = shopify.Transaction().find(
            #     order_id=str(self.shopify_order_id))

            shopify_transactions = refund_dict.get('transactions')
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
                    refund_invoice = self.env['account.move'].search([
                        ('state', '!=', 'cancel'),
                        ('shopify_order_id', '=', self.shopify_order_id),
                        ('shopify_config_id', '=', self.shopify_config_id.id),
                        '|', '|', ('shopify_transaction_id', '=',
                                   str(transaction_id)),
                        ('invoice_line_ids.shopify_transaction_id', '=',
                         str(transaction_id)),
                        ('shopify_transaction_id', '=', refund_dict.get('id')),
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
                                                                                           active_ids=(
                                                                                               invoice[0].ids)).create(
                                {'reason': "Shopify Refund", 'refund_method': 'refund',
                                 'date': self.date_order or fields.Datetime.now(),
                                 'journal_id': refund_journal_id and refund_journal_id.id or invoice[
                                     0].journal_id.id, })
                            reversal = move_reversal.reverse_moves()
                            refund_invoice = self.env['account.move'].browse(
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
                                    'account_id': unearned_account_id.id if unearned_account_id else refund_journal_id.default_account_id.id,
                                    'quantity': 1,
                                    'price_unit': float(amount),
                                    'shopify_transaction_id': str(transaction_id)})]
                            }
                            refund_invoice = self.env['account.move'].create(vals)
                        # Commented below 2 function call as they do not exist in v17
                        # refund_invoice.with_context(check_move_validity=False)._recompute_dynamic_lines(
                        #     recompute_all_taxes=True,
                        #     recompute_tax_base_amount=True)
                        # refund_invoice._check_balanced()
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
        This method will use to create shopify order payment for unfulfilled order using transaction of shopify order
        """
        payment_obj = self.env['account.payment']
        journal_id = False
        payment_method_id = False
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
        if gateway:
            gateway_id = self.shopify_payment_gateway_ids.filtered(lambda x: x.name == gateway)
            journal_id = gateway_id[0].pay_journal_id.id if gateway_id and gateway_id.pay_journal_id else False
            payment_method_id = gateway_id[0].in_pay_method_id.id if gateway_id and gateway_id.in_pay_method_id else False
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
        payment_vals = {'amount': amount,
                        'date': payment_date or self.date_order,
                        'payment_reference': self.name,
                        'partner_id': self.partner_id.commercial_partner_id.id,
                        'partner_type': 'customer',
                        'currency_id': self.currency_id.id,
                        'journal_id': journal_id,
                        'payment_type': payment_type,
                        'shopify_order_id': self.shopify_order_id,
                        'sale_order_id': self.id,
                        'payment_method_id': payment_method_id or False,
                        'shopify_transaction_id': transaction_id or False,
                        'shopify_config_id': self.shopify_config_id.id,
                        'shopify_name': self.shopify_order_name or self.name or False,
                        'shopify_gateway': gateway or False,
                        'company_id': self.shopify_config_id.default_company_id.id,
                        }
        if transaction_type == 'refund':
            payment_vals.update({'payment_type': 'outbound'})
        else:
            payment_vals.update({'payment_type': 'inbound'})
        if transaction_type in ['sale', 'refund', 'capture'] and status == 'success':
            payment = payment_obj.create(payment_vals)
            payment.action_post()

    def process_auto_workflow(self, order_dict, shopify_config):
        error_msg = ''
        move_obj = self.env['account.move']
        workflow_id = self.auto_workflow_id
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        if not workflow_id:
            raise UserError(_("Auto workflow not found."))
        if self.state in ['draft', 'sent'] and workflow_id.confirm_order:
            self.env.cr.commit()
            result_confirm = self.action_confirm()
            if result_confirm and isinstance(result_confirm, dict):
                exception_string = ''
                if (result_confirm.get('xml_id') and \
                        result_confirm['xml_id'] == \
                        'sale_exception.action_sale_exception_confirm'):
                    ctx = result_confirm.get('context')
                    default_value = self.env[
                        'exception.rule.confirm'].with_context(ctx).default_get([])
                    if default_value and default_value.get('exception_ids'):
                        exception_string += 'Order Imported. Base Order confirmed validation raised: \n'
                        exception_string += "\n".join(self.env[
                                                          'exception.rule'].browse(
                            default_value[
                                'exception_ids'][0][2]).mapped('description'))
                        if exception_string:
                            self.state = 'draft'
                            exception_string = 'Order Created Successfully but exception caused while confirming.\n' + exception_string
                            self.env.cr.commit()
                            raise ValidationError(_(exception_string))

        if self.state == 'sale':
            if workflow_id.register_payment:
                tag_ids = self.create_shopify_order_tags_in_odoo(order_dict.get('tags'))
                self.update_fulfilment_details_to_order(self, shopify_config)
                # for create shopify order payment with unearned revenue flow
                if tag_ids and shopify_config.is_pay_unearned_revenue and tag_ids in shopify_config.shopify_tag_ids:
                    if order_dict.get('fulfillment_status') == 'fulfilled':
                        self.create_shopify_direct_payment(shopify_config, self,
                                                           order_dict,
                                                           self.partner_id)
                    else:
                        self.create_shopify_payment(shopify_config, self, order_dict, self.partner_id)
                        self.update({'is_unearned_revenue_order': True})
                else:
                    self.create_shopify_direct_payment(shopify_config, self, order_dict, self.partner_id)
            # Process delivery orders/fulfillments
            ctx = {'shopify_order_id': self.shopify_order_id,
                   'shopify_log_id': shop_error_log_id}
            if workflow_id.create_invoice:
                ctx.update({'create_invoice': True,
                            'journal_id': workflow_id.sale_journal_id.id})
            if workflow_id.validate_invoice:
                ctx.update({'validate_invoice': True})
            fulfillment_status = order_dict.get('fulfillment_status')
            if fulfillment_status in ['fulfilled', 'partial']:
                try:
                    # self.fetch_order_fulfillment_location_from_shopify(order_dict)
                    self.with_context(ctx).process_shopify_order_fullfillment(
                        shopify_config, fulfillment_status=fulfillment_status,
                        fulfillment_lines=order_dict.get('fulfillments', []))
                except Exception as e:
                    pass
            financial_status = order_dict.get('financial_status')
            if financial_status in ['paid', 'partially_paid', 'voided',
                                    'partially_refunded', 'refunded']:
                posted_inv_ids = self.invoice_ids.filtered(
                        lambda i: i.move_type == 'out_invoice' and i.state == 'posted')
                all_posted_inv_ids = self.invoice_ids.filtered(
                    lambda i: i.move_type in ['out_invoice', 'out_refund'] and i.state == 'posted')
                if not any(posted_inv_ids) or sum(all_posted_inv_ids.mapped('amount_total_signed')) != self.amount_total:
                    self.create_shopify_invoice(shopify_config)
                    self.create_shopify_direct_payment(
                        shopify_config, self, order_dict, self.partner_id,
                        kind="sale")
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
                    invoice_ids = self.invoice_ids
                    if shopify_financial_status in ['refunded', 'partially_refunded']:
                        # Unfulfilled: create payment for un-fulfil order
                        if not fulfillment_status:
                            # for cancel in-progress DO
                            # picking_ids = self.picking_ids and self.picking_ids.filtered(
                            #     lambda x: not x.state == 'done' and x.location_dest_id.usage == 'customer') or False
                            # if picking_ids:
                            #     picking_ids.action_cancel()
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
                # Fulfilled: Create credit note from final invoice if Unearned revenue flow
        return True

    def shopify_order_cancel(self, cancelled_at, cancel_reason=False):
        cancel_datetime_utc = self.convert_date_utc(cancelled_at)
        self.with_context(cancel='True', disable_cancel_warning=True).action_cancel()
        self.shopify_cancelled_at = cancel_datetime_utc
        self.cancel_reason = cancel_reason

    def get_order_line_product(self, line, shopify_config):
        shopify_product_obj = self.env['shopify.product.template']
        shopify_product_variant_obj = self.env['shopify.product.product']
        shopify_variant_id = line.get('variant_id')
        shopify_product_id = line.get('product_id')
        sku = line.get('sku')
        barcode = line.get('barcode')
        shopify_product_product_id = False
        if shopify_variant_id:
            shopify_product_product_id = self.get_product(
                shopify_variant_id, shopify_product_id, shopify_config, sku,
                barcode)
        if shopify_product_product_id:
            product_id = shopify_product_product_id or False
            if not product_id:
                if shopify_config.is_create_product:
                    shopify_product_obj.shopify_import_product_by_ids(
                        shopify_config, shopify_product_id)
                    shopify_product_tmpl_id = shopify_product_variant_obj.search(
                        [('shopify_product_id', '=', str(shopify_variant_id)),
                         ('shopify_config_id', '=', shopify_config.id)],
                        limit=1)
                    product_id = shopify_product_tmpl_id.product_variant_id
                else:
                    product_id = self.env.ref(
                        'bista_shopify_connector.shopify_product')
                    # raise UserError(_("Product [%s] not found" % shopify_product_title))
        else:
            if shopify_config.is_create_product:
                try:
                    if shopify_product_id:
                        shopify_product_obj.shopify_import_product_by_ids(
                            shopify_config, shopify_product_id)
                except Exception as e:
                    raise UserError(_('Error occurs while creating product: '
                                      '%s' % (e)))
                shopify_product_tmpl_id = shopify_product_variant_obj.search(
                    [('shopify_product_id', '=', str(shopify_variant_id)),
                     ('shopify_config_id', '=', shopify_config.id)],
                    limit=1)
                if not shopify_product_tmpl_id:
                    shopify_custom_product_name = line.get(
                        'name') and line.get('name').strip()
                    product_id = self.get_shopify_custom_product(
                        shopify_custom_product_name)
                    if not product_id:
                        raise UserError(
                            _("Custom Product [%s] not found in Shopify Product Mapping" % shopify_custom_product_name))
                else:
                    product_id = shopify_product_tmpl_id.product_variant_id
        return product_id

    def _check_location_change(self, existing_order_id, fulfillment_order_dict):
        fulfillment_order_ids = []
        # line_items = {}
        fulfillment_item_ids = []
        orders_with_line_details = {}
        line_items = {}
        assigned_location_details = {}
        location_change = False
        for fulfillment_order in fulfillment_order_dict.get('fulfillment_orders'):
            if fulfillment_order.get('status') == 'open':
                lines = [str(line['id']) for line in fulfillment_order.get('line_items')]
                for line in fulfillment_order.get('line_items'):
                    assigned_location_details.update({str(line['id']): str(line.get('assigned_location_id'))})

                order = str(fulfillment_order['id'])
                fulfillment_item_ids += lines
                if lines and order:
                    orders_with_line_details.update({order: lines})
                fulfillment_order_ids.append(str(fulfillment_order.get('id')))
                for line_item in fulfillment_order.get('line_items'):
                    line_items[line_item.get('variant_id')] = line_item

        pickings = existing_order_id.picking_ids.filtered(
            lambda p: p.state not in ['cancel', 'done'] and p.shopify_order_id)
        if len(fulfillment_order_ids) >= 1:
            full_order_id_remove = []
            for picking in pickings:
                for move in picking.move_ids_without_package:
                    if (move.shopify_fulfillment_line_id in fulfillment_item_ids) and move.shopify_fulfillment_order_id in fulfillment_order_ids:
                        full_order_id_remove.append(move.shopify_fulfillment_order_id)
                        fulfillment_item_ids.remove(move.shopify_fulfillment_line_id)
                        if move.sale_line_id:
                            assign_loc_id = assigned_location_details.get(move.shopify_fulfillment_line_id)
                            if assign_loc_id:
                                if (move.sale_line_id.assigned_location_id != assign_loc_id):
                                    move.sale_line_id.write({'assigned_location_id': assign_loc_id})
                                    location_change = True
            for foir in list(set(full_order_id_remove)):
                fulfillment_order_ids.remove(foir)
            if fulfillment_order_ids or fulfillment_item_ids:
                done_pickings = existing_order_id.picking_ids.filtered(
                    lambda p: p.state in ['done'] and p.shopify_order_id)
                for picking in done_pickings:
                    for move in picking.move_ids_without_package:
                        if (move.shopify_fulfillment_line_id in fulfillment_item_ids) and move.shopify_fulfillment_order_id in fulfillment_order_ids:
                            fulfillment_order_ids.remove(move.shopify_fulfillment_order_id)
                            fulfillment_item_ids.remove(move.shopify_fulfillment_line_id)
                    if picking.shopify_fulfillment_id and (picking.shopify_fulfillment_id in fulfillment_order_ids):
                        fulfillment_order_ids.remove(picking.shopify_fulfillment_id)
        if len(fulfillment_item_ids) or len(fulfillment_order_ids) or location_change:
            pickings.filtered(lambda p: p.state not in ('done', 'cancel')).action_cancel()
            existing_order_id.with_context(cancel='True').action_cancel()
            existing_order_id.action_draft()
            for line in existing_order_id.order_line:
                move_state = list(set(line.move_ids.mapped('state')))
                if len(move_state) == 1 and move_state[0] == 'cancel':
                    flag_unlink = False
                    if (line.shopify_fulfillment_order_id and not orders_with_line_details.get(line.shopify_fulfillment_order_id)):
                        flag_unlink = True
                    if (line.shopify_fulfillment_order_id and orders_with_line_details.get(line.shopify_fulfillment_order_id)):
                        full_line_ids = orders_with_line_details.get(line.shopify_fulfillment_order_id)
                        if (line.shopify_fulfillment_line_id and line.shopify_fulfillment_line_id) not in full_line_ids:
                            flag_unlink = True
                    if flag_unlink:
                        line.unlink()
            return True
        return False
            # existing_order_id.process_auto_workflow(order_dict, shopify_config)

    def create_update_shopify_orders(self, order_dict, shopify_config, log_line_id):
        shopify_config.check_connection()
        risk_order_obj = self.env["shopify.risk.order"]
        shopify_product_obj = self.env['shopify.product.template']

        shopify_product_variant_obj = self.env['shopify.product.product']
        try:
            customer_name = ''
            customer_data = order_dict.get('customer')
            shopify_customer_id = customer_data and customer_data.get('id') or False
            partner_id = None
            if customer_data and shopify_customer_id:
                partner_id = self.get_customer(shopify_customer_id, shopify_config, customer_data)
            if customer_data and customer_data.get('first_name') and customer_data.get('last_name'):
                customer_name += customer_data.get('first_name') + customer_data.get('last_name')
            if not partner_id:
                if shopify_config.default_customer_id:
                    partner_id = shopify_config.default_customer_id
                if not partner_id:
                    raise UserError(_("Customer [%s] not found,please import customer first." % customer_name))
            self.fetch_order_fulfillment_location_from_shopify(order_dict)
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
                partner_id, billing_addr_id, shipping_addr_id, order_dict, shopify_config)
            order_vals.update({'fiscal_position_id': shopify_config.fiscal_shopify_id and shopify_config.fiscal_shopify_id.id or False,
                               'analytic_account_id': shopify_config.analytic_account_id and shopify_config.analytic_account_id.id or False,
                               'team_id': shopify_config.sale_team_id and shopify_config.sale_team_id.id or False})
            tags = order_dict.get('tags')
            tag_names = tags.split(',') if tags else []
            tag_names = [tag.strip() for tag in tag_names]
            tag_ids = self.env['shopify.tags'].search([('name', 'in', tag_names)])
            if tag_ids:
                user = self.env['user.shopify.tag'].search([('shopify_tag_ids', 'in', tag_ids.ids)], limit=1)
                if user:
                    order_vals.update({'user_id': user.user_id and user.user_id.id or False})
            shopify_line_items = order_dict.get('line_items')
            shopify_shipping_lines = order_dict.get('shipping_lines')
            taxes_included = order_dict.get('taxes_included')
            cancelled_at = order_dict.get('cancelled_at')
            cancel_reason = order_dict.get('cancel_reason')
            refunds = order_dict.get('refunds')
            shopify_total_price = order_dict.get(
                'total_price') and float(order_dict.get('total_price'))

            # fetch order fulfillments from shopify
            base_url = shopify_config.shop_url
            api_order_url = "/admin/api/2022-04/orders/%s/fulfillment_orders.json" % (
                shopify_order_id)
            url = base_url + api_order_url
            headers = {'X-Shopify-Access-Token': shopify_config.password}
            response = requests.request('GET', url, headers=headers)
            fulfillment_order_dict = response.json()
            assigned_location = {}
            fulfilment_items = []
            for fulfil_order in fulfillment_order_dict['fulfillment_orders']:
                for line_items in fulfil_order.get('line_items'):
                    line_items.update({'assigned_location_id': fulfil_order.get('assigned_location_id')})
                    fulfilment_items.append(line_items)
                    if assigned_location.get(line_items.get('line_item_id')):
                        assigned_location[line_items['line_item_id']].append([
                            fulfil_order.get('assigned_location_id'),
                            line_items.get('fulfillment_order_id'),
                            line_items.get('id'),
                            line_items.get('quantity')])
                    else:
                        assigned_location.update({
                            line_items.get('line_item_id'): [
                                [fulfil_order.get('assigned_location_id'),
                                 line_items.get('fulfillment_order_id'),
                                 line_items.get('id'),
                                 line_items.get('quantity')]
                            ]})
            if existing_order_id:
                # TODO: Update Order
                location_warehouse_vals = self.get_shopify_warehouse_location(order_dict, shopify_config)
                tag_ids = self.create_shopify_order_tags_in_odoo(order_dict.get('tags'))
                self.update_fulfilment_details_to_order(existing_order_id, shopify_config)
                existing_order_id.update({'warehouse_id': location_warehouse_vals['warehouse_id'].id,
                                          'shopify_tag_ids': [(6, 0, tag_ids.ids)] if tag_ids else False})
                has_change_location = self._check_location_change(existing_order_id, fulfillment_order_dict)
                if not cancelled_at:
                    order_line_list = []
                    for line in shopify_line_items:
                        for full_line in fulfilment_items:
                            if full_line.get('line_item_id') == line.get('id'):
                                order_line_id = existing_order_id.order_line.filtered(
                                    lambda l:
                                        l.shopify_line_id == str(line.get('id')) and
                                        l.shopify_fulfillment_order_id == str(full_line.get('fulfillment_order_id')) and
                                        l.shopify_fulfillment_line_id == str(full_line.get('id')))
                                if not order_line_id:
                                    product_id = self.get_order_line_product(line,
                                                                             shopify_config)
                                    shopify_line_id = line.get('id')
                                    fulfill_line = [full_line.get('assigned_location_id'),
                                                    full_line.get('fulfillment_order_id'),
                                                    full_line.get('id'),
                                                    full_line.get('quantity')]
                                    order_line_dict, tax_ids = self.prepare_order_line_vals(
                                        line, product_id, taxes_included,
                                        shopify_config, shopify_line_id, fulfill_line)
                                    order_line_dict.update({'shopify_line_change': True})
                                    order_line_list.append((0, 0, order_line_dict))
                                else:
                                    for order_line in order_line_id:
                                        vals_to_update = {}
                                        if order_line.assigned_location_id != str(full_line.get('assigned_location_id')):
                                            vals_to_update.update({'assigned_location_id': full_line.get('assigned_location_id')})
                                        if order_line.product_uom_qty != full_line.get('quantity'):
                                            if order_line.product_uom_qty < full_line.get('quantity'):
                                                move_qty = sum(
                                                    order_line.move_ids.filtered(lambda l: l.state == 'done').mapped(
                                                        'quantity')) or 0
                                                if move_qty > order_line.product_uom_qty:
                                                    raise ValidationError(_('''Can not decrease the product %s quantity to %s 
                                                    as %s quantity is already delivered.''' % (
                                                        order_line.product_id.display_name,
                                                        full_line.get('quantity'),
                                                        order_line.product_uom_qty)))
                                            vals_to_update.update({'product_uom_qty': full_line.get('quantity')})

                                        qty = full_line.get('quantity')
                                        new_unit_price = float(line.get(
                                            'price'))
                                        discount_lines = line.get(
                                            'discount_allocations', False)
                                        if discount_lines:
                                            discount_amount_total = self.get_discount_amount(
                                                discount_lines)
                                            if qty != 0:
                                                new_unit_price = (
                                                    new_unit_price - (
                                                        discount_amount_total / qty))
                                            if new_unit_price < 0.0:
                                                new_unit_price = 0.0
                                        if order_line.price_unit != new_unit_price:
                                            vals_to_update.update({
                                                'price_unit': new_unit_price,
                                                'shopify_discount_amount': discount_amount_total})
                                        if vals_to_update:
                                            vals_to_update.update(
                                                {'shopify_line_change': True})
                                            order_line.write(vals_to_update)

                    # prepare shipping lines in sale order lines
                    if not existing_order_id.order_line.filtered(
                            lambda l: l.is_delivery):
                        for line in shopify_shipping_lines:
                            code = line['code']
                            title = line['title']
                            carrier_id = self.get_carrier(
                                code, title, shopify_config)
                            shipping_line_dict = self.prepare_shipping_line_vals(
                                line, taxes_included,
                                shopify_config)
                            order_line_list.append(
                                (0, 0, shipping_line_dict))
                            order_vals.update(
                                {'carrier_id': carrier_id.id})

                    if order_line_list:
                        existing_order_id.write({'order_line': order_line_list})
                    tags = order_dict.get('tags')
                    tag_names = tags.split(',') if tags else []
                    tag_names = [tag.strip() for tag in tag_names]
                    tag_ids = self.env['shopify.tags'].search([('name', 'in',
                                                                tag_names)])
                    if tag_ids:
                        user = self.env['user.shopify.tag'].search([(
                            'shopify_tag_ids', 'in', tag_ids.ids)], limit=1)
                        if user:
                            existing_order_id.write({
                                'user_id': user.user_id and user.user_id.id or False})
                if has_change_location:
                    msg = _(
                        'Order and delivery canceled due to location change for some products. Order confirmed again '
                        'and new pickings generated: %s' % (", ".join(
                            existing_order_id.picking_ids.filtered(
                                lambda p: p.state not in ['cancel', 'done'] and p.shopify_order_id).mapped(
                                'name'))))
                    existing_order_id.message_post(body=msg)
                    # existing_order_id.location_change_refund(existing_order_id.invoice_ids)
                if cancelled_at:
                    # If cancelled_at and cancel reason, then cancel order in odoo
                    # cancel_datetime_utc = self.convert_date_utc(cancelled_at)
                    # existing_order_id.action_cancel()
                    existing_order_id.shopify_order_cancel(
                        cancelled_at, cancel_reason)
                else:
                    # Method call for processing order based on auto workflow
                    existing_order_id.process_auto_workflow(order_dict, shopify_config)
                # Process fulfillments for existing shopify orders. [Moved to process workflow]
                if refunds:
                    self.env['account.move'].create_update_shopify_refund(order_dict, shopify_config)
                    self.create_return_pickings(
                        shopify_config, existing_order_id, refunds)
                # REMOVED ERROR LOG for successful import
                # error_log_env.create_update_log(
                #     shop_error_log_id=shop_error_log_id,
                #     shopify_log_line_dict={'success': [
                #         {'error_message': "Update Order %s Successfully" % shopify_order_id,
                #          'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                # queue_liness 'processed', 'order_id': existing_order_id.id,
                # 'partner_id': existing_order_id.partner_id.id})
            else:

                # Create new order
                # Update Order vals with workflow data. If workflow not found, raise error
                workflow_vals = self.prepare_workflow_vals(order_dict, shopify_config)
                if workflow_vals:
                    order_vals.update(workflow_vals)
                # Prepare Sale order lines
                order_line_vals = []

                for line in shopify_line_items:
                    shopify_line_id = line.get('id')
                    product_id = self.get_order_line_product(line, shopify_config)
                    fullfillment_lines = assigned_location.get(shopify_line_id) if assigned_location else {}
                    for fulfill_line in fullfillment_lines:
                        line.update({'assigned_location_id': fulfill_line})
                        order_line_dict, tax_ids = self.prepare_order_line_vals(
                            line, product_id, taxes_included, shopify_config,
                            shopify_line_id, fulfill_line)
                        order_line_vals.append((0, 0, order_line_dict))
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
                    location_warehouse_vals = self.get_shopify_warehouse_location(order_dict, shopify_config)
                    order_vals.update({'order_line': order_line_vals,
                                       'warehouse_id': location_warehouse_vals['warehouse_id'].id})
                    if shopify_config.is_use_shop_seq:
                        shopify_order_name = order_dict.get('name')
                        order_vals.update({'name': shopify_order_name})
                    # order_vals.update({'ignore_exception': True})

                    order_vals.update({'shopify_source_name': order_dict.get(
                        'source_name', '') or ''})
                    order_id = self.create(order_vals)
                    # Method call for checking rounding diff
                    # self.check_rounding_diff(order_id, shopify_total_price, shop_error_log_id, queue_line_id)

                    # order_id.action_confirm()[Moved to workflow process]
                    # for create shopify order payment with unearned revenue flow [Moved to workflow process]
                    # if shopify_config.is_pay_unearned_revenue:
                    #     self.create_shopify_payment(shopify_config, order_id, order_dict, partner_id)
                    # else:
                    #     self.create_shopify_direct_payment(shopify_config, order_id, order_dict, partner_id)

                    # Method call for processing order based on auto workflow
                    if cancelled_at:
                        # If cancelled_at and cancel reason, then cancel order in odoo
                        # cancel_datetime_utc = self.convert_date_utc(cancelled_at)
                        # existing_order_id.action_cancel()
                        order_id.shopify_order_cancel(cancelled_at, cancel_reason)
                    else:
                        order_id.process_auto_workflow(order_dict, shopify_config)
                        # Process delivery orders/fulfillments [Moved to workflow process]
                    if refunds:
                        self.create_return_pickings(shopify_config, order_id, refunds)
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
                # error_log_existing_order_idenv.create_update_log(
                #     shop_error_log_id=shop_error_log_id,
                #     shopify_log_line_dict={'success': [
                #         {'error_message': "Import Order %s Successfully" % shopify_order_id,
                #          'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            related_model_id = False
            if existing_order_id:
                related_model_id = existing_order_id.id
            elif order_id:
                related_model_id = order_id.id
            log_line_id.update({
                'state': 'success',
                'related_model_name': 'sale.order',
                'related_model_id': related_model_id,
                'message':'Operation Successful'
            })
        except Exception as e:
            error_message = 'Failed to import Orders : {}'.format(e)
            log_line_id.update({
                'state': 'error',
                'message': error_message
            })
            # self.env.cr.commit()
            raise ValidationError(_(error_message))

    def process_return_order(self, order_dict, shopify_config, log_line_id=False):
        try:
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
                self.create_return_pickings(shopify_config, order_id, refunds)
            log_line_id.write({'state': 'success'})
        except Exception as e:
            error_message = 'Failed to import Return Orders : {}'.format(e)
            log_line_id.write({'state': 'error',
                               'message': error_message})
            self.env.cr.commit()
            raise UserError(_(error_message))

    def create_shopify_direct_payment(self, shopify_config, exist_order,
                                      order_dict, partner_id, kind=''):
        currency_obj = self.env['res.currency']
        error_log_env = self.env['shopify.error.log']
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
        payment_obj = self.env['account.payment']
        # payment_method_in = self.env.ref(
        #     "account.account_payment_method_manual_in")
        # TODO: if want to set with batch payment type
        # payment_method_in = self.env.ref(
        #     'account_batch_payment.account_payment_method_batch_deposit')
        try:
            if exist_order and financial_status in ('paid', 'partially_paid',
                                                    'refunded', 'partially_refunded'):
                # TODO: need to add time.sleep for multiple call error
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
                            tcurrency_id = shopify_config.default_company_id.currency_id
                        if not tcurrency_id:
                            error_message = "Currency %s not found in the system for transaction %s. " \
                                            "Please contact system Administrator." % (
                                                tcurrency, transaction_id)
                            error_log_env.create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={'error': [
                                    {'error_message': error_message}]})

                            continue
                        # TODO: Update it once we implement workflow
                        # auto_workflow_id = self.auto_workflow_id
                        # journal_id = auto_workflow_id.pay_journal_id
                        journal_id = False
                        if gateway:
                            gateway_id = exist_order.shopify_payment_gateway_ids.filtered(lambda x: x.name == gateway)
                            journal_id = gateway_id[0].pay_journal_id.id if gateway_id and gateway_id.pay_journal_id else False
                        if not journal_id:
                            error_message = 'Payment journal not found!'
                            error_log_env.create_update_log(
                                shop_error_log_id=shop_error_log_id,
                                shopify_log_line_dict={'error': [
                                    {'error_message': error_message}]})
                            continue
                        if not self.partner_id.commercial_partner_id:
                            self.partner_id._compute_commercial_partner()
                        invoice = exist_order.invoice_ids.filtered(
                            lambda i: i.state != 'cancel' and i.move_type ==
                                      'out_invoice' and i.payment_state not in ['paid', 'in_payment'])
                        if kind in ['sale', 'refund', 'capture'] and status == 'success':
                            reg_obj = self.env['account.payment.register']
                            reg_payment = reg_obj.with_context(
                                active_model='account.move',
                                active_ids=invoice.ids
                            ).create({
                                'payment_date': invoice.date,
                                'communication': invoice.name,
                                'amount': amount,
                                'journal_id': journal_id})._create_payments()
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
            error_log_env.create_update_log(
                shop_error_log_id=shop_error_log_id,
                shopify_log_line_dict={'error': [
                    {'error_message': error_message}]})

    def invoice_payment_reconciled_amount(self, payment_ids):
        """ This method will return amount of un-reconciled line for payments"""
        amount_lines = 0.00
        for payment in payment_ids:
            move_lines = payment.move_id.invoice_line_ids.filtered(
                lambda line: line.account_type in (
                    'asset_receivable', 'liability_payable') and not line.reconciled)
            for line in move_lines:
                amount_lines += abs(line.amount_residual)
        return amount_lines

    def create_rounding_diff(self, invoice, diff_amount_residual):
        """ This method will create rounding diff line in shopify invoice"""
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
                    'quantity': round_qty,
                    'price_unit': abs(diff_amount_residual)})],
                 'is_rounding_diff': True})

    def create_shopify_invoice(self, shopify_config):
        error_log_env = self.env['shopify.error.log']
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        if not shop_error_log_id:
            shop_error_log_id = error_log_env.create_update_log(
                shopify_config_id=shopify_config, operation_type='import_order')
        journal_id = self._context.get('journal_id')
        if not journal_id:
            journal_id = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', shopify_config.default_company_id.id)],
                limit=1).id
        should_generate_invoice = False
        if any(self.order_line.filtered(lambda s: s.product_id.invoice_policy
                                                  == 'order' and
                                                  s.product_uom_qty > s.qty_invoiced)):
            should_generate_invoice = True

        if should_generate_invoice:
            context = {
                'active_model': 'sale.order',
                'active_ids': self.ids,
                'active_id': self.id,
                'default_journal_id': journal_id,
                'default_deposit_account_id': shopify_config.unearned_account_id.id,
                # 'default_account_id': shopify_config.unearned_account_id.id,
                'default_shopify_config_id': shopify_config.id,
                'default_sale_order_id': self.id,
                'shopify_order_id': self.shopify_order_id,
                'open_invoices': False
            }
            adv_invoice_id = self.env['sale.advance.payment.inv'].with_context(context).create({
                'advance_payment_method': 'delivered',
                'deduct_down_payments': True,
                # 'fixed_amount': amount,
                # 'deposit_account_id': shopify_config.unearned_account_id.id,
            })
            adv_invoice_id.with_context(
                default_shopify_order_id=self.shopify_order_id,
                default_invoice_date=self.date_order).create_invoices()
            new_invoice = self.invoice_ids.filtered(lambda r: r.state == 'draft')
            new_invoice.write({'shopify_order_id': self.shopify_order_id,
                               'sale_order_id': self.id,
                               'shopify_config_id': shopify_config.id})
            new_invoice.action_post()
            for inv in self.invoice_ids.filtered(
                    lambda iv: iv.move_type == 'out_invoice' and iv.payment_state != 'paid' and iv.state != 'cancel'):
                if inv.amount_residual > 0.0 and not self.is_unearned_revenue_order:
                    # for final invoice reconciled
                    payment_ids = self.env['account.payment'].search(
                        [('sale_order_id', '=', self.id),
                         ('shopify_order_id', '=', self.shopify_order_id),
                         ('shopify_config_id', '=', shopify_config.id),
                         ("state", '!=', 'cancelled')])
                    if payment_ids:
                        amount_lines = self.invoice_payment_reconciled_amount(
                            payment_ids)
                        # added for round diff create line unearned revenue flow
                        diff_amount_residual = round(
                            inv.amount_residual - float(amount_lines), 5)
                        self.create_rounding_diff(inv, diff_amount_residual)
                        # end rounding diff code
                    inv.filtered(lambda r: r.state == 'draft').action_post()
                    for payment in payment_ids:
                        move_lines = payment.move_id.invoice_line_ids.filtered(
                            lambda line: line.account_type in (
                                'liability_payable', 'asset_receivable') and not line.reconciled)
                        for line in move_lines:
                            inv.js_assign_outstanding_line(line.id)
                    if inv.amount_residual > 0.0:
                        error_log_env.create_update_log(
                            shop_error_log_id=shop_error_log_id,
                            shopify_log_line_dict={'error': [
                                {'error_message': "Please process an invoice %s for order %s manually, as it is "
                                                  "not completely paid." % (
                                                      inv.name, self.name)}]})
                else:
                    moves_creditnote = False
                    if self.remaining_downpayment > 0:
                        dp_amount = self.remaining_downpayment
                        if dp_amount > inv.amount_total:
                            dp_amount = inv.amount_total
                        # added for round diff create line unearned revenue flow
                        diff_amount_residual = round(
                            inv.amount_residual - dp_amount, 5)
                        self.create_rounding_diff(inv, diff_amount_residual)
                        # end rounding diff code
                        if dp_amount > 0:
                            moves_creditnote = self.manual_create_downpayment_invoice(
                                movetype='out_refund', amount=dp_amount)
                    inv.filtered(lambda r: r.state == 'draft').action_post()
                    if moves_creditnote:
                        lines = inv.line_ids.filtered(lambda x: (x.account_id.reconcile or x.account_id.internal_type == 'liquidity') and not x.reconciled)
                        for line in lines:
                            counterpart_lines = moves_creditnote.line_ids.filtered(
                                lambda x: x.account_id == line.account_id
                                          and x.currency_id == line.currency_id
                                          and not x.reconciled)
                            (line + counterpart_lines).reconcile()
                    if inv.amount_residual > 0.0:
                        error_log_env.create_update_log(
                            shop_error_log_id=shop_error_log_id,
                            shopify_log_line_dict={'error': [
                                {'error_message': "Please process an invoice %s for order %s manually, as it is "
                                                  "not completely paid." % (inv.name, self.name)}]})
        return True

    def create_shopify_payment(self, shopify_config, exist_order, order_dict, partner_id):
        currency_obj = self.env['res.currency']
        error_log_env = self.env['shopify.error.log']
        financial_status = order_dict.get('financial_status')
        shop_order_id = order_dict.get('id')
        order_name = order_dict.get('name')
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        payment_obj = self.env['account.payment']
        inv_obj = self.env['account.move']
        auto_workflow_id = self.auto_workflow_id

        journal_sale = self.env['account.journal'].search(
            [('type', '=', 'sale'),
             ('company_id', '=', shopify_config.default_company_id.id)],
            limit=1)
        if exist_order and financial_status in ('paid', 'partially_paid',
                                                'refunded', 'partially_refunded'):
            transactions = []
            # try: TODO: need to add time sleep for resolved multiple call error
            transactions = shopify.Transaction.find(order_id=shop_order_id)
            payment_date = exist_order.date_order or False
            for transaction in transactions:
                transaction_data = transaction.attributes
                transaction_id = transaction_data.get('id')
                status = transaction_data.get('status')
                kind = transaction_data.get('kind')
                msg = transaction_data.get('message')
                gateway = transaction_data.get('gateway')
                journal_id = False
                payment_method_id = False
                if gateway:
                    gateway_id = exist_order.shopify_payment_gateway_ids.filtered(lambda x: x.name == gateway)
                    journal_id = gateway_id[0].pay_journal_id.id if gateway_id and gateway_id.pay_journal_id else False
                    payment_method_id = gateway_id[0].in_pay_method_id.id if gateway_id and gateway_id.in_pay_method_id else False
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
                        error_log_env.create_update_log(
                            shop_error_log_id=shop_error_log_id,
                            shopify_log_line_dict={'error': [
                                {'error_message': error_message}]})

                        continue
                    invoice = inv_obj.search([
                        ('shopify_order_id', '=', str(shop_order_id)),
                        ('sale_order_id', '=', self.id),
                        ('is_downpayment_inv', '=', True),
                        ('move_type', '=', 'out_invoice')], limit=1)
                    if not invoice:
                        invoice = exist_order.manual_create_downpayment_invoice(
                            movetype='out_invoice', amount=amount)
                    if not invoice:
                        # TODO: need to add warning for it
                        continue
                    invoice.update({
                        'journal_id': journal_sale.id,
                        'shopify_config_id': shopify_config.id,
                        'shopify_order_id': exist_order.shopify_order_id})

                    payments = payment_obj.search([(
                        'shopify_transaction_id', '=', transaction_id),
                        ('shopify_config_id', '=', shopify_config.id),
                        ("state", '!=', 'cancelled')])
                    if not payments:
                        payment_vals = {
                            'journal_id': journal_id,
                            'amount': amount,
                            'partner_id': partner_id.id,
                            'currency_id': tcurrency_id.id,
                            'date': payment_date,
                            'payment_reference': self.name,
                            'ref': invoice.name if invoice else '',
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'payment_method_id': payment_method_id,
                            'shopify_transaction_id': transaction_id,
                            'shopify_note': msg,
                            'shopify_gateway': gateway,
                            'shopify_order_id': shop_order_id,
                            'shopify_name': order_name,
                            'shopify_config_id': shopify_config.id,
                            'company_id': shopify_config.default_company_id.id,
                        }
                        payment = payment_obj.create(
                            payment_vals)
                        payment.action_post()

                        move_lines = payment.move_id.invoice_line_ids.filtered(
                            lambda line: line.account_type in (
                                'asset_receivable',
                                'liability_payable') and not line.reconciled)
                        for line in move_lines:
                            invoice.js_assign_outstanding_line(line.id)

            return True

    def fetch_all_shopify_orders(self, from_order_date=False, to_order_date=False):
        """return: shopify draft order list"""
        processed_at_min = self.env['ir.config_parameter'].sudo().get_param('shopify.order.min.datetime') or ''
        if processed_at_min:
            date_format = "%d/%m/%Y %H:%M:%S"
            processed_at_min = datetime.strptime(processed_at_min, date_format)
        try:
            shopify_draft_order_list = []
            page_info = False
            while 1:
                if from_order_date and to_order_date:
                    if page_info:
                        page_wise_draft_order_list = shopify.Order().find(
                            limit=250, page_info=page_info, status='any')
                    else:
                        page_wise_draft_order_list = shopify.Order().find(
                            updated_at_min=from_order_date,
                            updated_at_max=to_order_date,
                            processed_at_min=processed_at_min,
                            limit=250, status='any')
                else:
                    if page_info:
                        page_wise_draft_order_list = shopify.Order().find(
                            limit=250, page_info=page_info, status='any')
                    else:
                        page_wise_draft_order_list = shopify.Order().find(
                            limit=250, status='any')
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

    def shopify_import_order_by_ids(self, shopify_config, shopify_order_by_ids):
        """ TODO: Create queue and then process it like import orders """

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Orders",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_order',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_config.check_connection()
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            order_list = []
            # shopify_log_line_dict = self.env.context.get('shopify_log_line_dict',
            #                                              {'error': [], 'success': []})
            # shopify_log_id = error_log_env.create_update_log(
            #     shopify_config_id=shopify_config,
            #     operation_type='import_order_by_ids')
            for order in ''.join(shopify_order_by_ids.split()).split(','):
                try:
                    order_list.append(shopify.Order().find(order))
                except:
                    raise ValidationError(
                        'Order Not Found! Please enter valid Order ID!')
            seconds = 10
            for shopify_order in order_list:
                shopify_order_dict = shopify_order.to_dict()
                gateway = shopify_order_dict.get('gateway')
                if not self_cr.check_shopify_gateway(gateway, shopify_config):
                    self_cr.create_shopify_payment_gateway(gateway, shopify_config)

                name = shopify_order_dict.get('name', '') or ''
                job_descr = _("Create/Update Sales Order:   %s") % (
                        name and name.strip())
                log_line_vals.update({
                    'name': job_descr,
                    'id_shopify': f"Customer: {shopify_order_dict.get('id') or ''}",
                    'parent_id': parent_log_line_id.id
                })
                log_line_id = shopify_log_line_obj.create(log_line_vals)

                eta = datetime.now() + timedelta(seconds=seconds)
                self_cr.with_company(shopify_config.default_company_id).with_delay(
                    description=job_descr, max_retries=5,
                    eta=eta).create_update_shopify_orders(shopify_order_dict,
                                                          shopify_config, log_line_id)
                seconds += 1

            # if not shopify_log_id.shop_error_log_line_ids and not self.env.context.get('shopify_log_id', False):
            #     shopify_log_id and shopify_log_id.unlink()
            # return shopify_product_template_id
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })
            cr.commit()
        except Exception as e:
            cr.rollback()
            parent_log_line_id.update({
                'state': 'error',
                'message': e,
            })
            self.env.cr.commit()
            raise ValidationError(_(e))

    def shopify_import_return_orders(self, shopify_config):
        """This method is used to create queue and queue line for orders"""
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Locations",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_return',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            shopify_config.check_connection()
            last_return_order_import_date, parameter_id = shopify_config.get_update_value_from_config(
                operation='read', field='last_return_order_import_date', shopify_config_id=shopify_config,
                field_value='')

            from_order_date = last_return_order_import_date or fields.Datetime.now()
            to_order_date = fields.Datetime.now()
            shopify_order_list = self_cr.fetch_all_shopify_orders(
                from_order_date, to_order_date)
            if shopify_order_list:
                seconds = 30
                for shopify_orders in tools.split_every(250, shopify_order_list):
                    for order in shopify_orders:
                        order_dict = order.to_dict()
                        if not order_dict.get('refunds'):
                            continue
                        refund_data = order_dict.get('refunds')
                        if not all(refund_line.get('restock') for refund_line in refund_data):
                            continue
                        name = order_dict.get('name', '')
                        eta = datetime.now() + timedelta(seconds=seconds)
                        job_descr = _("Import Sales Order Return:   %s") % (
                                name and name.strip())
                        log_line_vals.update({
                            'name': job_descr,
                            'id_shopify': order_dict.get('id') or '',
                            'parent_id': parent_log_line_id.id
                        })
                        log_line_id = shopify_log_line_obj.create(log_line_vals)
                        self_cr.with_company(shopify_config.default_company_id).with_delay(
                            description=job_descr, max_retries=5, eta=eta
                        ).process_return_order(
                            order_dict, shopify_config, log_line_id=log_line_id)
                        seconds += 2
            shopify_config.get_update_value_from_config(
                operation='write', field='last_return_order_import_date', shopify_config_id=shopify_config,
                field_value=str(datetime.now().strftime('%Y/%m/%d %H:%M:%S')), parameter_id=parameter_id)
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
            raise ValidationError(_(e))

    def create_shopify_payment_gateway(self, gateway, shopify_config):
        """
        This Method create shopify payment gateway when queue of orders is created.
        """
        gateway = gateway or 'blank_gateway'
        in_pay_method_id = self.env['account.payment.method'].search([
            ('payment_type', '=', 'inbound'),
            ('code', '=', 'manual')],
            limit=1)
        shopify_gateway = self.env['shopify.payment.gateway'].create({'name': gateway,
                                                                      'code': gateway,
                                                                      'shopify_config_id': shopify_config.id,
                                                                      'in_pay_method_id': in_pay_method_id.id,
                                                                      'pay_journal_id': shopify_config.default_payment_journal_id.id})

    def check_shopify_gateway(self, gateway, shopify_config):
        """
        This method checks whether payment gateway received in order data exists in the system or not in shopify payment gatewatys list
        """
        gateway = gateway or 'blank_gateway'
        shopify_gateway = self.env['shopify.payment.gateway'].sudo().search(
            [('code', '=', gateway), ('shopify_config_id', '=', shopify_config.id)], limit=1)
        if not shopify_gateway:
            in_pay_method_id = self.env['account.payment.method'].search([
                ('payment_type', '=', 'inbound'),
                ('code', '=', 'manual')],
                limit=1)
            shopify_gateway = self.env['shopify.payment.gateway'].create({
                'name': gateway,
                'code': gateway or 'blank_gateway',
                'shopify_config_id': shopify_config.id,
                'in_pay_method_id': in_pay_method_id.id,
                'pay_journal_id': shopify_config.default_payment_journal_id.id
            })
        return shopify_gateway or False

    def shopify_import_orders(self, shopify_config, from_date=False, to_date=False, is_order_by_date_range=False):
        """This method is used to create queue and queue line for orders"""
        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Import Orders",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'import_order',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

        self.env.cr.commit()
        cr = registry(self._cr.dbname).cursor()
        self_cr = self.with_env(self.env(cr=cr))

        try:
            shopify_log_line_obj = self_cr.env['shopify.log.line']
            shopify_config.check_connection()
            # is_order_by_date_range = self.env.context.get(
            #     'is_order_by_date_range', False)
            last_import_order_date, parameter_id = shopify_config.get_update_value_from_config(
                operation='read', field='last_import_order_date', shopify_config_id=shopify_config, field_value='')

            from_order_date = from_date or last_import_order_date or fields.Datetime.now()
            to_order_date = to_date or fields.Datetime.now()
            shopify_order_list = self_cr.fetch_all_shopify_orders(
                from_order_date, to_order_date)

            if shopify_order_list:
                payment_gateway = []
                seconds = 30
                for order in shopify_order_list:
                    order_dict = order.to_dict()
                    # name = "%s %s" % (order_dict.get('first_name', ''),
                    #                   order_dict.get('last_name', ''))
                    name = order_dict.get('name', '')
                    eta = datetime.now() + timedelta(seconds=seconds)
                    job_descr = _("Create/Update Sales Order:   %s") % (
                            name and name.strip())
                    log_line_vals.update({
                        'name': job_descr,
                        'id_shopify': order_dict.get('id') or '',
                        'parent_id': parent_log_line_id.id
                    })
                    log_line_id = shopify_log_line_obj.create(log_line_vals)

                    self_cr.with_company(shopify_config.default_company_id).with_delay(
                        description=job_descr, max_retries=5,
                        eta=eta).create_update_shopify_orders(
                        order_dict, shopify_config, log_line_id=log_line_id)
                    payment_gateway.append(order_dict.get('gateway'))
                    seconds += 2
                # Code for checking shopify payment gateway and create if does not exist
                for gateway in list(set(payment_gateway)):
                    if not self_cr.check_shopify_gateway(gateway, shopify_config):
                        self_cr.create_shopify_payment_gateway(
                            gateway, shopify_config)

            if not is_order_by_date_range:
                shopify_config.get_update_value_from_config(
                    operation='write', field='last_import_order_date', shopify_config_id=shopify_config,
                    field_value=str(datetime.now().strftime('%Y/%m/%d %H:%M:%S')), parameter_id=parameter_id)
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
            raise ValidationError(_(e))

    def prepare_shopify_fulfillment_line_vals_for_kit_products(self, picking_id, product_moves, line_items_dict):
        return

    def prepare_shopify_fulfillment_line_vals(self, picking_id, order_lines):
        line_items_dict = {}
        product_moves = picking_id.move_ids.filtered(
            lambda x: x.sale_line_id.product_id.id == x.product_id.id and x.state == "done")
        for move in product_moves.filtered(lambda line: line.product_id.detailed_type == 'product'):
            fulfillment_line_id = move.shopify_fulfillment_line_id
            assigned_location_id = move.shopify_assigned_location_id
            if line_items_dict.get(move.shopify_fulfillment_order_id):
                line_items_dict[move.shopify_fulfillment_order_id].append(
                    {"id": fulfillment_line_id,
                     "quantity": int(move.product_qty),
                     "assigned_location_id":assigned_location_id})
            else:
                line_items_dict.update({
                    move.shopify_fulfillment_order_id: [
                        {"id": fulfillment_line_id,
                         "quantity": int(move.product_qty),
                         "assigned_location_id": assigned_location_id}]})
        self.prepare_shopify_fulfillment_line_vals_for_kit_products(picking_id, product_moves, line_items_dict)
        return line_items_dict

    def prepare_fulfillment_vals(
            self, sale_order, shopify_location_id, picking, line_items):
        tracking_info = {}
        shopify_order = shopify.Order().find(sale_order.shopify_order_id)
        fulfillment_orders = shopify_order.get('fulfillment_orders')
        if picking.carrier_id:
            tracking_info.update({"company": picking.carrier_id.name or ''})
        if picking.carrier_tracking_ref:
            tracking_info.update({
                "number": picking.carrier_tracking_ref,
                "url": picking.carrier_tracking_url or ''})
        fulfillment_line_item_ids = [l.get('id') for l in line_items]
        picking_fulfillment_ids = (
            picking.move_ids_without_package.filtered(
                lambda m: m.shopify_fulfillment_line_id in
                          fulfillment_line_item_ids).mapped(
                'shopify_fulfillment_order_id'))
        fulfillment_order_id = [str(full.get('id')) for full in
                                fulfillment_orders
                                if full.get('id') and str(full.get('id')) in
                                picking_fulfillment_ids]

        fulfillment_vals = {
            'location_id': shopify_location_id,
            "notify_customer": True,
            "line_items_by_fulfillment_order": [
                {
                    "fulfillment_order_id": fulfillment_order_id[0] if
                    fulfillment_order_id and fulfillment_order_id[0] else
                    fulfillment_orders[0].get(
                        'id'),
                    "fulfillment_order_line_items": line_items
                }]
        }
        if tracking_info:
            fulfillment_vals.update({"tracking_info": tracking_info})
        return fulfillment_vals

    def shopify_update_order_status(self, shopify_config, picking_ids=False):
        cr = registry(self._cr.dbname).cursor()
        old_cr = self.env.cr
        self_cr = self.with_env(self.env(cr=cr))

        shopify_log_line_obj = self_cr.env['shopify.log.line']
        log_line_vals = {
            'name': "Update Order Status",
            'shopify_config_id': shopify_config.id,
            'operation_type': 'update_order_status',
        }
        parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
        self_cr.env.cr.commit()
        try:
            self_cr = self.with_env(self.env(cr=old_cr))
            shopify_config.check_connection()
            if not picking_ids:
                picking_ids = self_cr.env['stock.picking'].search([
                    ('shopify_config_id', '=', shopify_config.id),
                    ('is_updated_in_shopify', '=', False),
                    ('state', '=', 'done'),
                    ('location_dest_id.usage', '=', 'customer')], order='date')

            seconds = 10
            for picking in picking_ids:
                self_cr.update_fulfilment_details_to_order(
                    picking.sale_id, shopify_config)
                carrier_name = picking.carrier_id or picking.carrier_id.name or ''
                sale_order = picking.sale_id
                order_lines = sale_order.order_line
                list_of_tracking_number = [picking.carrier_tracking_ref] if picking.carrier_tracking_ref else []
                tracking_url = [picking.carrier_tracking_url or '']
                line_item_list = []

                line_item_list = self_cr.prepare_shopify_fulfillment_line_vals(
                    picking, order_lines)
                for line_item_key in line_item_list:
                    line_item_dict = line_item_list.get(line_item_key)
                    shopify_location_id = (
                        line_item_dict[0].get('assigned_location_id'))
                    # location_mapping_id = self.get_picking_mapping_location(
                    #     picking, shopify_config)
                    # shopify_location_id = location_mapping_id.shopify_location_id
                    if shopify_location_id:
                        for rem_dict in line_item_dict:
                            if rem_dict.get('assigned_location_id'):
                                del rem_dict['assigned_location_id']
                        name = picking.name
                        eta = datetime.now() + timedelta(seconds=seconds)
                        job_descr = _("Update Fulfillment to Shopify:   %s") % (
                                name and name.strip())
                        log_line_id = shopify_log_line_obj.create({
                            'name': job_descr,
                            'shopify_config_id': shopify_config.id,
                            'operation_type': 'update_order_status',
                            'parent_id': parent_log_line_id.id
                        })
                        self_cr.with_delay(
                            description=job_descr, max_retries=5, eta=eta
                        ).update_create_fulfillment(
                            picking, shopify_location_id, line_item_dict,
                            log_line_id)
                        seconds += 2
                    else:
                        raise ValidationError('Shipment is not associated with Shopify..!')
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful',
            })
            cr.commit()
        except Exception as e:
            self_cr.env.cr.rollback()
            error_message = 'Failed to create fulfillment for Order : {}'.format(
                e)
            parent_log_line_id.update({
                'state': 'error',
                'message': error_message,
            })
            cr.commit()
            raise ValidationError(_(e))

    def update_create_fulfillment(
            self, picking, shopify_location_id, line_item_dict, log_line_id):
        try:
            picking.sale_id.shopify_config_id.check_connection()
            fulfillment_vals = self.prepare_fulfillment_vals(
                picking.sale_id, shopify_location_id, picking, line_item_dict)
            new_fulfillment = shopify.fulfillment.FulfillmentV2(fulfillment_vals)
            fulfilment = new_fulfillment.save()
            shopify_fulfillment_id = False
            if fulfilment:
                shopify_fullment_result = xml_to_dict(new_fulfillment.to_xml())
                shopify_fulfillment_id = shopify_fullment_result.get(
                    'fulfillment').get('id') or ''
                picking.write({'is_updated_in_shopify': True,
                               'shopify_fulfillment_id': shopify_fulfillment_id,
                               })
            log_line_id.update({
                'id_shopify': f'Fulfillment: {shopify_fulfillment_id}',
                'state': 'success',
                'related_model_name': 'stock.picking',
                'related_model_id': picking.id,
            })
        except Exception as e:
            error_message = 'Failed to create fulfillment for Order : {}'.format(
                e)
            log_line_id.update({
                'state': 'error',
                'message': error_message
            })
            raise UserError(_(error_message))


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
    shopify_location_id = fields.Char("Shopify Location", copy=False)
    shopify_fulfillment_line_id = fields.Char("Fulfillment Line ID", copy=False)
    shopify_fulfillment_order_id = fields.Char("Fulfillment Order ID",
                                               copy=False)
    assigned_location_id = fields.Char(
        'Assigned Location', copy=False,
        help="Shopify Assigned location id for line item")

    shopify_line_change = fields.Boolean(string="Shopify Line Change")
    shopify_shipping_line = fields.Boolean(string="Shopify Shipping Line")

    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice',
                 'qty_invoiced', 'shopify_line_change')
    def _compute_invoice_status(self):
        super(SaleOrderLine, self)._compute_invoice_status()
        for line in self:
            if line.shopify_line_change:
                line.invoice_status = 'invoiced'

    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(
            group_id=group_id)
        if values.get('sale_line_id'):
            sale_line_id = self.browse([values.get('sale_line_id')])
            shopify_location_id = sale_line_id.assigned_location_id
            if not shopify_location_id:
                shopify_location_id = sale_line_id.shopify_location_id
            if shopify_location_id:
                location_id = self.env['shopify.location.mapping'].search([
                    ('shopify_location_id', '=', shopify_location_id),
                    ('shopify_config_id', '=',
                     sale_line_id.order_id.shopify_config_id.id)],
                    limit=1)
                values.update({
                    'warehouse_id': location_id.warehouse_id or False})
        return values


class SaleDownpaymentHistory(models.Model):
    _name = 'sale.downpayment.history'
    _description = 'Sale Downpayment History'

    sale_id = fields.Many2one('sale.order', string="Order", copy=False)
    amount = fields.Float(string="Amount")
    invoice_id = fields.Many2one('account.move', string="Invoice")
