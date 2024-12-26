##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _, tools
from odoo.exceptions import AccessError, ValidationError
from .. import shopify
import urllib.parse as urlparse
import pprint
from odoo.exceptions import UserError
import requests


class AccountMove(models.Model):
    _inherit = "account.move"

    shopify_transaction_id = fields.Char(string='Shopify Transaction ID',
                                         copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        tracking=True,
                                        copy=False)
    shopify_order_id = fields.Char(string='Shopify Order ID', copy=False)
    sale_order_id = fields.Many2one("sale.order", string="Sale Order",
                                    copy=False)
    shopify_hist_data = fields.Boolean('Shopify Historical Data', copy=False)
    is_partially_refunded = fields.Boolean('Is Partially Refunded', copy=False)
    fulfillment_status = fields.Char('Fulfillment Status', copy=False)
    shopify_adj_amount = fields.Boolean('Shopify Adjustment', copy=False)
    is_downpayment_inv = fields.Boolean('Down Payment Inv', copy=False)
    is_downpayment_refund = fields.Boolean('Down Payment Refund', copy=False)
    is_rounding_diff = fields.Boolean('Rounding Diff Inv', copy=False)
    settlement_downpayment = fields.Boolean('Settlement Downpayment',
                                            copy=False)
    settlement_refund_id = fields.Char('Settlement Refund ID', copy=False)
    is_manual_shopify_payment = fields.Boolean('Manual Shopify Payment', default=False)
    is_manual_odoo_refund = fields.Boolean('Manual Odoo Refund To Shopify', default=False)

    @api.model_create_multi
    def create(self, vals):
        record = super(AccountMove, self).create(vals)
        for rec in record:
            if rec.stock_move_id:
                rec.update({'date': self._context.get(
                    'force_period_date') or rec.stock_move_id.date})
        return record

    def fetch_all_shopify_orders(self, shopify_config):
        """
            This methods fetchs all the shopify orders from
            the given specific dates or based on the entered
            order IDs.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        try:
            shopify_refunds_list = []
            page_info = False
            while 1:
                if shopify_config.last_refund_import_date:
                    if page_info:
                        page_wise_refund_list = shopify.Order.find(
                            limit=250, page_info=page_info)
                    else:
                        page_wise_refund_list = shopify.Order.find(
                            updated_at_min=shopify_config.last_refund_import_date,
                            limit=250, status='any')
                else:
                    if page_info:
                        page_wise_refund_list = shopify.Order.find(
                            limit=250, page_info=page_info)
                    else:
                        page_wise_refund_list = shopify.Order.find(
                            limit=250, status='any')
                page_url = page_wise_refund_list.next_page_url
                parsed = urlparse.parse_qs(page_url)
                page_info = parsed.get('page_info', False) and \
                    parsed.get('page_info', False)[0] or False
                shopify_refunds_list = page_wise_refund_list + shopify_refunds_list
                if not page_info:
                    break
            return shopify_refunds_list
        except Exception as e:
            raise AccessError(e)

    def shopify_import_refund_orders(self, shopify_config):
        """
            This method is used to create queue and queue line for orders
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        shopify_config.check_connection()
        shopify_order_list = self.fetch_all_shopify_orders(shopify_config)
        if shopify_order_list:
            # payment_gateway = []
            for shopify_orders in tools.split_every(150, shopify_order_list):
                shop_queue_id = shopify_config.action_create_queue(
                    'import_refund')
                for order in shopify_orders:
                    order_dict = order.to_dict()
                    if not order_dict.get('refunds'):
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
                    # payment_gateway.append(order_dict.get('gateway'))
            # # Code for checking shopify payment gateway and create if does not exist
            # for gateway in list(set(payment_gateway)):
            #     if not self.check_shopify_gateway(gateway, shopify_config):
            #         self.create_shopify_payment_gateway(gateway, shopify_config)

        shopify_config.sudo().write({'last_import_order_date':fields.Datetime.now()})
        return True

    def create_update_shopify_refund(self, order_data, shopify_config):
        """
            Create refunds from shopify queue line data
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        shopify_config.check_connection()
        order_env = self.env['sale.order'].sudo()
        tax_env = self.env['account.tax']
        shopify_prd_var_env = self.env['shopify.product.product']
        shopify_prd_map_env = self.env['shopify.product.mapping']
        partner_env = self.env['res.partner'].sudo()
        product_env = self.env['product.product']
        currency_env = self.env['res.currency']
        company_id = shopify_config.default_company_id.id
        shopify_cust_id = shopify_config.default_customer_id.id
        error_log_env = self.env['shopify.error.log'].sudo()
        shop_error_log_id = self.env.context.get('shopify_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        shipping_product = self.env.ref(
            'bista_shopify_connector.shopify_shipping_product')
        is_partially_refunded = False
        shop_order_id = str(order_data.get('id'))
        get_refunds = shopify.Refund.find(order_id=shop_order_id)
        if not get_refunds:
            error_message = "Facing a problem while importing return.\n"\
                "Please make sure while importing a return you have to do a refund first of the order then you will be able to import the return."
                # "Please make sure while doing return you should have to refund then go for return."
            error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                            shopify_log_line_dict={'error': [
                                                {'error_message': error_message,
                                                 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.sudo().write({'state': 'failed'})
            return True
        # refunds = isinstance(get_refunds, list) and get_refunds[0] \
        #     or isinstance(get_refunds, dict) or []
        refunds = isinstance(get_refunds, list) and get_refunds or isinstance(get_refunds, dict) or []
        if not refunds:
            # TODO: Generate error log here if necessary
            error_message = "Facing a problem while importing return.\n"\
                "Please make sure while importing a return you have to do a refund first of the order then you will be able to import the return."
                # "Please make sure while doing return you should have to refund then go for return."
            error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                            shopify_log_line_dict={'error': [
                                                {'error_message': error_message,
                                                 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.write({'state': 'failed'})
            return True

        try:
            if not self.is_manual_shopify_payment:
                for refund in refunds:
                    trans = refund.attributes.get('transactions')
                    for transaction in trans:
                        refund_transaction_data = transaction.attributes
                        refund_trans_id = refund_transaction_data.get('id')
                        shopify_transaction = self.search([('shopify_transaction_id','=',refund_trans_id)])
                        if shopify_transaction:
                            pass
                        else:
                            refund_dict = refund.attributes
                            order_id = refund_dict.get('order_id')
                            order = order_env.search([('shopify_order_id', '=', order_id)])
                            if not order:
                                error_message = "Facing a problems while importing refund.\n" \
                                                "shopify order id!: %s not found in Odoo" % (
                                                    order_id or '')
                                error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                                shopify_log_line_dict={'error': [
                                                                    {'error_message': error_message,
                                                                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                queue_line_id and queue_line_id.write({'state': 'failed'})
                                return True
                            fulfillment_status = order_data.get('fulfillment_status')
                            # Author : Yogeshwar Chaudhari
                            # Date   : 21/12/23
                            # As per purity client requirment/business i have comment below code.They are not 
                            # going to make return document of shopify into odoo they want only refund for restock.
                            # restock = refund_dict.get('restock')
                            # if not restock and fulfillment_status != 'fulfilled':
                            #     shopify_transactions = shopify.Transaction().find(
                            #         order_id=str(order.shopify_order_id))
                            #     for transaction in shopify_transactions:
                            #         transaction_dict = transaction.to_dict()
                            #         order.create_shopify_order_payment(
                            #             transaction_dict, 'outbound')
                            #     queue_line_id and queue_line_id.write({'state': 'processed'})
                            #     return True
                            auto_workflow_id = order.auto_workflow_id
                            if order_data.get('financial_status') == "partially_refunded":
                                is_partially_refunded = True

                            refund_journal_id = auto_workflow_id and auto_workflow_id.credit_note_journal_id or None
                            # refund_journal_id = shopify_config.credit_note_journal_id
                            order_name = order_data.get('name')
                            taxes_included = order_data.get('taxes_included')
                            currency = order_data.get('currency')
                            tcurrency_id = currency_env.search(
                                [('name', '=', currency)], limit=1)
                            customer = order_data.get('customer')
                            cust = shopify_config.default_customer_id
                            unearned_account_id = False
                            if fulfillment_status not in ('partial', 'fulfilled'):
                                unearned_account_id = shopify_config.unearned_account_id

                            shipping_id = False
                            billing_id = False
                            if customer:
                                cust_id = customer.get('id')
                                partner = partner_env.search([('shopify_customer_id', '=',
                                                               cust_id)], limit=1)
                                partner_id = partner and partner.id
                                if not partner:
                                    partner_env.shopify_import_customer_by_ids(shopify_config, shopify_customer_by_ids=cust_id,
                                                                               queue_line=self._context.get('queue_line_id'))
                                    partner = partner_env.search(
                                        [('shopify_customer_id', '=', cust_id)], limit=1)
                                    partner_id = partner and partner.id or shopify_cust_id
                            else:
                                partner_id = shopify_cust_id
                                partner = shopify_config.default_customer_id
                            #  TODO: Billing address has some issue so for now using partner_id
                            # if order_data.get('shipping_address'):
                            #     shipping_data = order_data.get(
                            #         'shipping_address').attributes
                            #     shipping_id = order.create_shipping_or_billing_address(
                            #         shipping_data, partner_id, 'invoice')
                            # TODO: Billing address has some issue so for now using partner_id
                            # if order_data.get('billing_address'):
                            #     billing_data = order_data.get('billing_address').attributes
                            #     billing_id = order.create_shipping_or_billing_address(
                            #         billing_data, partner_id, 'delivery')
                            # Start Prepare vals for shipping lines
                            line_vals_dict = {}
                            shipping_total = 0.0
                            ship_tax_price = 0.0
                            for shipping_line_data in order_data.get('shipping_lines'):
                                line_prod_name = shipping_line_data.get(
                                    'title').encode('utf-8')
                                if shipping_line_data.get('handle'):
                                    handle_str = " / " + shipping_line_data.get(
                                        'handle').encode('utf-8')
                                    line_prod_name += handle_str
                                shipping_total += round(
                                    float(shipping_line_data.get('price', 0.0)), 2)
                                line_prod_price = shipping_line_data.get('price') or 0
                                shipping_tax_ids = []
                                # if str(order_data.get('total_tax')) not in ['0.0', '0.00']:
                                #     for tax_line in shipping_line_data.get(
                                #             'tax_lines'):
                                #         ship_tax_price += round(float(tax_line.get('price', 0.0)), 2)
                                #         rate = float(tax_line.get('rate', 0.0))
                                #         tax_calc = rate * 100
                                #         country_code = partner and partner.country_id and partner.country_id.code + ' ' or ''
                                #         name = rate and tax_line.get('title') + ' ' + country_code + str(
                                #             round(tax_calc, 4)) or tax_line.get('title')
                                #         if  taxes_included:
                                #             name += "Price_included"
                                #         shopify_tax = tax_env.search(
                                #             [('name', '=', name),
                                #              ('type_tax_use', '=', 'sale'),
                                #              ('amount', '=', float(tax_calc)),
                                #              ('price_include', '=', taxes_included),
                                #              ('company_id', '=', company_id)])
                                #         if not shopify_tax:
                                #             tax_vals = {
                                #                 'name': name,
                                #                 'amount': float(tax_calc),
                                #                 'price_include': 'false',
                                #                 'type_tax_use': 'sale',
                                #                 'company_id': company_id
                                #             }
                                #             shopify_tax = tax_env.create(tax_vals)
                                #         # Set default tax account in tax repartition line
                                #         lines = shopify_tax.invoice_repartition_line_ids.filtered(
                                #             lambda i: i.repartition_type == 'tax')
                                #         if lines and shopify_config.default_tax_account_id:
                                #             lines.account_id = shopify_config.default_tax_account_id.id
                                #         lines = shopify_tax.refund_repartition_line_ids.filtered(
                                #             lambda i: i.repartition_type == 'tax')
                                #         if lines and shopify_config.default_tax_account_id:
                                #             lines.account_id = shopify_config.default_tax_account_id.id
                                #         shipping_tax_ids.append(shopify_tax[0].id)
                                line_vals_dict.update({
                                    'product_id': shipping_product.id,
                                    'name': 'Shipping refund',
                                    'display_type': 'product',
                                    'price_unit': 0.0,
                                    'quantity': 1,
                                    'tax_ids': [(6, 0, shipping_tax_ids)],
                                    'account_id': refund_journal_id.default_account_id.id,
                                    # 'analytic_account_id': shopify_config.analytic_account_id.id,
                                    # 'account_id': unearned_account_id and unearned_account_id.id or,
                                    # refund_journal_id.loss_account_id.id,
                                })
                            # end shipping line
                            app_index = []
                            trans = refund_dict.get('transactions')
                            if not trans:
                                error_message = "Facing a problems while importing refund.\n" \
                                                "shopify order id!: %s transactions not found in Odoo" % (
                                                    order_id or '')
                                error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                                shopify_log_line_dict={'error': [
                                                                    {'error_message': error_message,
                                                                     'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                queue_line_id and queue_line_id.write({'state': 'failed'})
                                return True
                            kind_list = []
                            transaction_list = []
                            for transaction in trans:
                                refund_transaction_data = transaction.attributes
                                status = refund_transaction_data.get('status')
                                transaction_list.append(refund_transaction_data.get('id'))
                                if status == 'success':
                                    kind_list.append(refund_transaction_data.get('kind'))
                            if 'refund' not in kind_list:
                                return True
                            refund_id = refund_dict.get('id')
                            note = refund_dict.get('note')

                            custom_context = {
                                'active_model': 'sale.order',
                                'active_ids': [order.id],
                                'active_id': order.id,
                            }
                            # for order adjustment
                            order_adj_des = False
                            ship_adj_des = False
                            ship_adj_amt = 0.0
                            for oa in refund_dict.get('order_adjustments'):
                                ord_adj_data = oa.attributes
                                kind = ord_adj_data.get('kind')
                                if kind == 'refund_discrepancy':
                                    order_adj_des = True
                                elif kind == 'shipping_refund':
                                    ship_adj_des = True
                                    ship_adj_amt += abs(float(ord_adj_data.get('amount')))
                                    if taxes_included:
                                        ship_adj_amt += abs(float(ord_adj_data.get('tax_amount')))
                            # end order adjustment
                            # start code refunds line
                            if refund_dict.get('refund_line_items') and not order_adj_des:
                                line_lst = []
                                product_missing = False
                                subtotal = 0.0
                                # end shipping order adjustment
                                for refund_lines in refund_dict.get('refund_line_items'):
                                    prd_id = False
                                    refund_lines_data = refund_lines.attributes
                                    ref_line_qty = refund_lines_data.get('quantity')
                                    line = refund_lines_data.get('line_item')
                                    if not line:
                                        continue
                                    line_data = line.attributes
                                    name = line_data.get('name')
                                    sku = line_data.get('sku')
                                    restock_type = refund_lines_data.get('restock_type')
                                    if restock_type != 'return' and order.downpayment_history_ids:
                                        unearned_account_id = shopify_config.unearned_account_id
                                    var_id = line_data.get('variant_id')
                                    refund_line_id = refund_lines_data.get('id')
                                    line_item_id = refund_lines_data.get('line_item_id')
                                    description = line_data.get('name')

                                    price_unit = float(line_data.get('price'))
                                    qty = int(ref_line_qty)  # line_data.get('quantity')
                                    # TODO - Check with Ashvin whether we need this or not
                                    # if float(ref_line_qty) != float(line_data.get('quantity')):
                                    #     error_message = "Please review Credit Note for order: %s" % order_name
                                    #     error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                    #                                     shopify_log_line_dict={'error': [
                                    #                                         {'error_message': error_message,
                                    #                                          'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                    #     queue_line_id and queue_line_id.write({'state': 'failed'})
                                    # Check if credit note exists or not
                                    credit_note = False
                                    credit_notes = self.search([
                                        ('state', '!=', 'cancel'),
                                        ('shopify_order_id', '=', str(order_id)), '|',
                                        ('shopify_transaction_id', '=', str(refund_id)),
                                        ('shopify_transaction_id', 'in', transaction_list),
                                        ('shopify_config_id', '=', shopify_config.id),
                                        ('sale_order_id', '=', order.id),
                                        ('move_type', '=', 'out_refund')])
                                    for cr in credit_notes:
                                        if cr.invoice_line_ids.filtered(lambda l: l.refund_id == str(refund_line_id) or l.shopify_transaction_id == str(refund_line_id)):
                                            credit_note = cr.id
                                            break
                                    if credit_note:
                                        queue_line_id and queue_line_id.write(
                                            {'state': 'processed', 'refund_id': credit_note or False})
                                        continue
                                    if var_id:
                                        domain = [('shopify_product_id', '=', var_id)]
                                        prd = shopify_prd_var_env.search(domain, limit=1)
                                        prd_id = prd.product_variant_id.id
                                    if not prd_id and sku:
                                        domain = [('default_code', '=', sku)]
                                        prd = product_env.search(domain, limit=1)
                                        prd_id = prd and prd.id or False
                                    if not prd_id:
                                        domain = [('shopiy_product_name', '=', name)]
                                        prd = shopify_prd_map_env.search(domain, limit=1)
                                        if prd:
                                            prd_id = prd.product_variant_id \
                                                and prd.product_variant_id.id \
                                                or False
                                    if not prd_id:
                                        domain = [('shopify_name', '=', name)]
                                        prd = product_env.search(domain, limit=1)
                                        prd_id = prd and prd.id or False
                                    if not prd_id:
                                        product_missing = True
                                        error_message = "Refund for order %s is imported as " \
                                                        "product %s : %s not found." % (
                                                            order_name, name, sku)
                                        error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                                        shopify_log_line_dict={'error': [
                                                                            {'error_message': error_message,
                                                                             'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                        queue_line_id and queue_line_id.write({'state': 'failed'})

                                    uom_id = prd.product_variant_id.uom_id.id
                                    # inline discount code
                                    if line_data.get(
                                        'discount_allocations') and line_data.get(
                                            'quantity') > 0:
                                        for disc_data in line_data.get(
                                                'discount_allocations'):
                                            discount_data = disc_data.attributes
                                            price_unit = price_unit - (float(
                                                discount_data.get(
                                                    'amount')) / line_data.get(
                                                'quantity') or 0)
                                            app_index.append(discount_data.get(
                                                'discount_application_index'))
                                    total = qty * price_unit
                                    subtotal += total
                                    tax_ids = []
                                    if str(refund_lines_data.get(
                                            'total_tax')) not in ['0.0', '0.00']:
                                        for tax_line in line_data.get(
                                                'tax_lines'):
                                            rate = float(
                                                tax_line.attributes.get('rate',
                                                                        0.0))
                                            tax_calc = rate * 100
                                            country_code = partner and partner.country_id and partner.country_id.code + ' ' or ''
                                            name = rate and tax_line.attributes.get('title') + ' ' + country_code + str(
                                                round(tax_calc, 4)) or tax_line.attributes.get('title')
                                            if taxes_included:
                                                name += " Price_included"
                                            shopify_tax = tax_env.search([
                                                ('name', '=', name),
                                                ('type_tax_use', '=', 'sale'),
                                                ('amount', '=', float(tax_calc)),
                                                ('price_include', '=', taxes_included),
                                                ('company_id', '=', company_id)
                                                ])
                                            if not shopify_tax:
                                                tax_vals = {
                                                    'name': name,
                                                    'amount': float(tax_calc),
                                                    'price_include': 'true',
                                                    'type_tax_use': 'sale',
                                                    'company_id': company_id
                                                }
                                                shopify_tax = tax_env.create(tax_vals)
                                            # Set default tax account in tax repartition
                                            # line
                                            lines = shopify_tax.invoice_repartition_line_ids.filtered(
                                                lambda i: i.repartition_type == 'tax')
                                            if lines and shopify_config.default_tax_account_id:
                                                lines.account_id = shopify_config.default_tax_account_id.id
                                            lines = shopify_tax.refund_repartition_line_ids.filtered(
                                                lambda i: i.repartition_type == 'tax')
                                            if lines and shopify_config.default_tax_account_id:
                                                lines.account_id = shopify_config.default_tax_account_id.id
                                            tax_ids.append(shopify_tax[0].id)
                                    inv_line_vals = (
                                        {
                                        'product_id': prd_id, 'name': description,
                                        'price_unit': price_unit, 'product_uom_id': uom_id,
                                        'quantity': qty,
                                        'tax_ids': tax_ids and [(6, 0, tax_ids)] or [(6, 0, [])],
                                        'refund_id': refund_line_id,
                                        'restock_type': restock_type,
                                        'display_type': 'product',
                                        'account_id': refund_journal_id.default_account_id.id,})
                                    line_lst.append((0, 0, inv_line_vals))
                                # end code refunds line
                                if line_lst and not product_missing:
                                    # for added shipping order adjustment
                                    if line_vals_dict:
                                        if ship_adj_des:
                                            line_vals_dict['price_unit'] = ship_adj_amt
                                            line_lst.append((0, 0, line_vals_dict))
                                    created_order_at = refund_dict.get('created_at')
                                    local_datetime = shopify_config.convert_shopify_datetime_to_utc(
                                        created_order_at)
                                    partner_id = partner_id or cust.id
                                    if order.invoice_ids:
                                        invoice_id = order.invoice_ids.filtered(lambda move: move.move_type == 'out_invoice')
                                        partner_id = invoice_id and invoice_id[0].partner_id.id
                                        # if invoice_id:
                                        #     discount_invoice_line = invoice_id.invoice_line_ids.filtered(lambda inv: any(
                                        #     line.price_unit < 0 and line.product_id.type == 'service' for line in inv))
                                        #     for line in discount_invoice_line:
                                        #         line_data = {
                                        #             'product_id': line.product_id.id,
                                        #             'quantity': line.quantity,
                                        #             'price_unit': line.price_unit,
                                        #             'restock_type': restock_type,
                                        #             'display_type': 'product',
                                        #             'account_id': refund_journal_id.default_account_id.id,
                                        #             'tax_ids': [(6,0, line.tax_ids.ids)]
                                        #         }
                                        #         line_lst.append((0, 0, line_data))
                                    vals = {
                                        'move_type': 'out_refund',
                                        'ref': 'Reversal of: %s' % order.name,
                                        'invoice_origin': order_name,
                                        'invoice_date': str(local_datetime),
                                        # billing_id and billing_id.id or partner_id,
                                        'partner_id': partner_id,
                                        'shopify_order_id': order_id,
                                        'shopify_transaction_id': refund_id,
                                        'currency_id': tcurrency_id.id,
                                        'invoice_line_ids': line_lst,
                                        'narration': note,
                                        'company_id': company_id,
                                        'shopify_config_id': shopify_config.id,
                                        'journal_id': refund_journal_id.id,
                                        # shipping_id and shipping_id.id or partner_id,
                                        'partner_shipping_id': partner_id,
                                        'fulfillment_status': fulfillment_status,
                                        'sale_order_id': order.id,
                                    }
                                    # Added below condition to stop extra credit-note creation while doing refund from odoo to shopify.
                                    exit_credit_notes = self.search([
                                        ('state', '!=', 'cancel'),
                                        ('shopify_transaction_id', '=', str(refund_id)),
                                        ('sale_order_id', '=', order.id),
                                        ('move_type', '=', 'out_refund')])
                                    if not exit_credit_notes:
                                        exist_move = self.create(vals)
                                        if shopify_config.is_refund_auto_paid:
                                            # for existing move create payment for refunds
                                            exist_move.action_post()
                                            shopify_transactions = shopify.Transaction().find(
                                                order_id=str(order.shopify_order_id))
                                            for transaction in shopify_transactions:
                                                transaction_dict = transaction.to_dict()
                                                amount = transaction_dict.get('amount')
                                                gateway = transaction_dict.get('gateway')
                                                transaction_id = transaction_dict.get('transaction',
                                                                                      {}).get('id') or transaction_dict.get('id')
                                                transaction_type = transaction_dict.get('transaction', {}).get(
                                                    'kind') or transaction_dict.get('kind')
                                                status = transaction_dict.get('transaction', {}).get(
                                                    'status') or transaction_dict.get('status')
                                                msg = transaction_dict.get('message')
                                                # if transactions are completed create payment else continue
                                                if transaction_type not in ['refund'] or status != 'success':
                                                    continue
                                                if transaction_type in ['sale', 'refund', 'capture'] and status == 'success':
                                                    reg_payment = self.env['account.payment.register'].with_context(
                                                        active_model='account.move', active_ids=[exist_move.id]).create(
                                                        {
                                                            'payment_date': exist_move.date,
                                                            'communication': exist_move.name,
                                                            'amount': amount,
                                                        }
                                                    )._create_payments()
                                                    if reg_payment:
                                                        reg_payment.write({
                                                            'sale_order_id': order.id,
                                                            'shopify_order_id': shop_order_id,
                                                            'shopify_transaction_id': transaction_id or False,
                                                            'shopify_gateway': gateway or False,
                                                            'shopify_note': msg,
                                                            'shopify_name': order_name,
                                                            'shopify_config_id': shopify_config.id,
                                                        })

                                                # def search_shop_payment():
                                                #     return self.env['account.payment'].search([
                                                #         ('shopify_order_id', '=', order.shopify_order_id),
                                                #         ('shopify_config_id', '=', shopify_config.id),
                                                #         ('shopify_transaction_id',
                                                #          '=', str(transaction_id)),
                                                #         ('payment_type', '=', 'outbound'),
                                                #         ("state", '!=', 'cancelled')])
                                                # payment_id = search_shop_payment()
                                                # if not payment_id:
                                                #     order.create_shopify_order_payment(
                                                #         transaction_dict, 'outbound')
                                                #     payment_id = search_shop_payment()
                                                # # for reconciled credit note
                                                # for rinv in exist_move:
                                                #     if order.downpayment_history_ids:
                                                #         rinv.update({'is_downpayment_refund': True})
                                                #     move_lines = payment_id.move_id.invoice_line_ids.filtered(
                                                #         lambda line: line.account_type in (
                                                #             'asset_receivable',
                                                #             'liability_payable') and not line.reconciled)
                                                #     for line in move_lines:
                                                #         rinv.js_assign_outstanding_line(line.id)
                                        queue_line_id and queue_line_id.write(
                                            {'state': 'processed', 'refund_id': exist_move.id})
                                    else:
                                        pass
                            else:
                                # trans = data.get('transactions')
                                line_list = []
                                vals = {}

                                transaction_id = ''
                                for transaction in trans:
                                    refund_transaction_data = transaction.attributes
                                    if shopify_config.is_refund_auto_paid:
                                        # for create payment for refunds
                                        order.create_shopify_order_payment(
                                            refund_transaction_data, 'outbound')
                                    transaction_id = refund_transaction_data.get('id')
                                    credit_note = False
                                    # Check if credit note exists or not
                                    credit_notes = self.search([
                                        ('state', '!=', 'cancel'),
                                        ('shopify_order_id', '=', str(order_id)), '|',
                                        ('shopify_transaction_id', '=', str(refund_id)),
                                        ('shopify_transaction_id', '=', str(transaction_id)),
                                        ('shopify_config_id', '=', shopify_config.id),
                                        ('sale_order_id', '=', order.id),
                                        ('move_type', '=', 'out_refund')])
                                    for refund_lines in refund_dict.get('refund_line_items'):
                                        refund_line_id = refund_lines_data.get('id')
                                        for cr in credit_notes:
                                            if cr.invoice_line_ids.filtered(
                                                    lambda l: l.shopify_transaction_id == str(transaction_id) or l.shopify_transaction_id == str(refund_line_id)):
                                                credit_note = cr.id
                                                break
                                    if credit_note:
                                        queue_line_id and queue_line_id.write(
                                            {'state': 'processed', 'refund_id': credit_note or False})
                                        continue
                                    msg = refund_transaction_data.get('message')
                                    status = refund_transaction_data.get('status')
                                    kind = refund_transaction_data.get('kind')
                                    tcurrency = refund_transaction_data.get('currency')
                                    tcurrency_id = currency_env.search(
                                        [('name', '=', tcurrency)], limit=1)
                                    rt_amount = refund_transaction_data.get('amount')
                                    amount = isinstance(rt_amount, str) and float(rt_amount) \
                                        or rt_amount
                                    if status == 'success' and kind == 'refund' \
                                            and not credit_note:
                                        is_invoice_found = False
                                        if not is_invoice_found:
                                            line_list.append((0, 0, {
                                                'name': note or msg,
                                                'account_id': refund_journal_id.default_account_id.id,
                                                # 'analytic_account_id': shopify_config.analytic_account_id.id,
                                                'quantity': 1,
                                                'price_unit': amount,
                                                'display_type': 'product',
                                                'shopify_transaction_id': str(transaction_id), }))
                                local_datetime = shopify_config.convert_shopify_datetime_to_utc(refund_dict.get(
                                    'created_at'))
                                vals.update({
                                    'shopify_config_id': shopify_config.id,
                                    'sale_order_id': order.id,
                                    'invoice_date': str(local_datetime),
                                    'ref': 'Reversal of: %s' % order.name,
                                    'partner_id': partner_id or cust.id,  # billing_id and billing_id.id or cust.id,
                                    'journal_id': refund_journal_id.id,
                                    'currency_id': tcurrency_id.id,
                                    'move_type': 'out_refund',
                                    'shopify_transaction_id': refund_id,
                                    'shopify_order_id': order_id,
                                    'invoice_line_ids': line_list,
                                    'invoice_origin': order_name or '',
                                    'is_partially_refunded': is_partially_refunded,
                                    'shopify_adj_amount': order_adj_des,
                                    'fulfillment_status': fulfillment_status,
                                })
                                if line_list:
                                    try:
                                        credit_note = self.with_context(
                                            custom_context).create(vals)
                                        if shopify_config.is_refund_auto_paid:
                                            credit_note.action_post()
                                            # for reconciled payment of refunds
                                            payment_id = self.env['account.payment'].search([
                                                ('shopify_order_id', '=', order.shopify_order_id),
                                                ('shopify_config_id', '=', shopify_config.id),
                                                ('sale_order_id', '=', order.id),
                                                ('shopify_transaction_id', '=', str(transaction_id)),
                                                ('payment_type', '=', 'outbound'),
                                                ("state", '!=', 'cancelled')])
                                            # for reconciled credit note
                                            for rinv in credit_note:
                                                if order.downpayment_history_ids:
                                                    rinv.update({'is_downpayment_refund': True})
                                                move_lines = payment_id.move_id.invoice_line_ids.filtered(
                                                    lambda line: line.account_type in (
                                                        'asset_receivable',
                                                        'liability_payable') and not line.reconciled)
                                                for line in move_lines:
                                                    rinv.js_assign_outstanding_line(line.id)
                                        queue_line_id and queue_line_id.write(
                                            {'state': 'processed', 'refund_id': credit_note.id})
                                    except Exception as e:
                                        error_message = "Facing a problems while importing " \
                                            "refund order!: %s : %s" % (
                                                        order.name or '', e)
                                        error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                                                        shopify_log_line_dict={'error': [
                                                                            {'error_message': error_message,
                                                                             'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                                        queue_line_id and queue_line_id.write({'state': 'failed'})
                            shopify_config.sudo().write({'last_import_order_date':fields.Datetime.now()})
                return True
            else:
                pass
        except Exception as e:
            error_message = f"Facing a problems while importing refund order!: {e}"
            error_log_env.sudo().create_update_log(shop_error_log_id=shop_error_log_id,
                                            shopify_log_line_dict={'error': [
                                                {'error_message': error_message,
                                                 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            queue_line_id and queue_line_id.write({'state': 'failed'})
    
    def shopify_refund(self, credit_note_id, reason):
        shopify_shipping_product_id = credit_note_id.shopify_config_id.shipping_product_id
        shipping_line_id = credit_note_id.invoice_line_ids.filtered(
            lambda r: r.product_id.id == shopify_shipping_product_id.id)
        shipping_amount = shipping_line_id and shipping_line_id.price_subtotal or 0.0
        refund_lines = credit_note_id.invoice_line_ids.filtered(
            lambda r: r.product_id and r.product_id.type != 'service')
        line_ids = [(0, 0, {'product_id': line.product_id.id,
                            'quantity': line.quantity,
                            'shopify_line_id': line.sale_line_ids.shopify_line_id,
                            }) for line in refund_lines]
        order_shipping_amount = 0.0
        if shipping_line_id:
            order_shipping_amount = shipping_line_id.sale_line_ids and shipping_line_id.sale_line_ids[
                0].price_subtotal or 0.0
        self.env['shopify.export.refund'].create({'shipping_refund_amount': shipping_amount,
                                                  'total_refund_amount': credit_note_id.amount_total,
                                                  'currency_id': credit_note_id.sale_order_id.currency_id.id,
                                                  'credit_note_id': credit_note_id.id,
                                                  'refund_line_ids': line_ids,
                                                  'order_shipping_amount': order_shipping_amount,
                                                  'restock_type': 'no_restock',
                                                  'refund_reason': reason,
                                                  'no_lines': False if len(refund_lines) > 0 else True,
                                                  }).refund_in_shopify()

    def action_open_refund_wizard(self):
        """
            Opens wizard for creating refund in shopify.
            @author: Ashwin Khodifad @Bista Solutions Pvt. Ltd.
        """
        if not self.shopify_order_id:
            raise UserError(
                _("You cannot create refund in shopify as this invoice is not for shopify order."))
        if self.shopify_transaction_id:
            raise UserError(
                _("Refund already created in shopify with ID %s." % self.shopify_transaction_id))
        shopify_shipping_product_id = self.shopify_config_id.shipping_product_id
        shipping_line_id = self.invoice_line_ids.filtered(
            lambda r: r.product_id.id == shopify_shipping_product_id.id)
        shipping_amount = shipping_line_id and shipping_line_id.price_subtotal or 0.0
        refund_lines = self.invoice_line_ids.filtered(
            lambda r: r.product_id and r.product_id.type != 'service')
        line_ids = [(0, 0, {'product_id': line.product_id.id,
                            'quantity': line.quantity,
                            'shopify_line_id': line.sale_line_ids.shopify_line_id,
                            }) for line in refund_lines]
        order_shipping_amount = 0.0
        if shipping_line_id:
            order_shipping_amount = shipping_line_id.sale_line_ids and shipping_line_id.sale_line_ids[
                0].price_subtotal or 0.0
        context = dict(self._context)
        context.update({'default_shipping_refund_amount': shipping_amount,
                        'default_total_refund_amount': self.amount_total,
                        'default_currency_id': self.sale_order_id.currency_id.id,
                        'default_credit_note_id': self.id,
                        'default_refund_line_ids': line_ids,
                        'default_order_shipping_amount': order_shipping_amount,
                        'default_no_lines': False if len(refund_lines) > 0 else True,
                        })

        return {
            'name': _('Refund order In Shopify'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'shopify.export.refund',
            'target': 'new',
            'context': context,
        }

    def update_payment_in_shopify(self):
        shopify_config = self.env['shopify.config']
        shopify_config_id = shopify_config.search([('state','=', 'success')],limit=1)
        sale_order_id = self.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
        shop_url = shopify_config_id.shop_url
        api_key =  shopify_config_id.api_key
        password = shopify_config_id.password
        ORDER_ID = int(sale_order_id.shopify_order_id)
        if not ORDER_ID:
            raise UserError(
                _("You cannot create payment in shopify as this invoice is not for shopify order."))
        endpoint = f'{shop_url}/admin/api/2023-07/orders/{ORDER_ID}/transactions.json'
        payload = {
            "transaction": {
                "kind": "capture",
                "amount": str(self.amount_total),
                "currency": "USD"
            }
        }
        response = requests.post(endpoint, json=payload, auth=(api_key, password))
        if response.status_code == 201:
            self.write({'is_manual_shopify_payment':True})
            sale_order_id.write({'is_manual_shopify_payment':True})


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    refund_id = fields.Char(string='Refund Line ID', copy=False)
    restock_type = fields.Char('Shopify Restock Type', copy=False)
    shopify_transaction_id = fields.Char(string='Transaction ID', copy=False)
    sale_order_id = fields.Many2one('sale.order',  related='payment_id.sale_order_id')
    shopify_transaction_id = fields.Char(string='Shopify Transaction', related='payment_id.shopify_transaction_id',
                                         copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Config",
                                        help="Enter Shopify Configuration",
                                        tracking=True, related='payment_id.shopify_config_id',
                                        copy=False)
    shopify_note = fields.Char(string='Shopify Note', related='payment_id.shopify_note', copy=False)
    shopify_gateway = fields.Char(string='Shopify Gateway', related='payment_id.shopify_gateway', copy=False)
    shopify_order_id = fields.Char(string='Shopify Order ID', related='payment_id.shopify_order_id', copy=False)
    shopify_name = fields.Char(string='Shopify Order', related='payment_id.shopify_name', copy=False)

    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        """
            Constraints to be by pass
            @author: Yogeshwar Chaudhari @Bista Solutions Pvt. Ltd.
        """
        for line in self:
            pass

    # Method to add rounding diff account in invoice
    # def _get_computed_account(self):
    #     res = super(AccountMoveLine, self)._get_computed_account()
    #     shopify_config_id = self.move_id.shopify_config_id
    #     product_id = self.env.ref('bista_shopify_connector.shopify_rounding_diff_product')
    #     if shopify_config_id and shopify_config_id.rounding_diff_account_id and self.product_id.id == product_id.id:
    #         return shopify_config_id.rounding_diff_account_id
    #     return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one('sale.order')
    shopify_transaction_id = fields.Char(string='Shopify Transaction ID',
                                         copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        tracking=True,
                                        copy=False)
    shopify_note = fields.Char(string='Shopify Note', copy=False)
    shopify_gateway = fields.Char(string='Shopify Gateway', copy=False)
    shopify_order_id = fields.Char(string='Shopify Order ID', copy=False)
    shopify_name = fields.Char(string='Shopify Order Name', copy=False)

    @api.model_create_multi
    def create(self, vals):
        record = super(AccountPayment, self).create(vals)
        for rec in record:
            if rec.stock_move_id:
                rec.update({'date': self._context.get(
                    'force_period_date') or rec.stock_move_id.date})
        return record
