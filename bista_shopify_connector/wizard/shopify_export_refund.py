##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from datetime import datetime, timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from .. import shopify


class ShopifyExportRefundLine(models.TransientModel):
    _name = "shopify.export.refund.line"
    _description = "Export Shopify Refund Line"

    refund_id = fields.Many2one('shopify.export.refund', string='Refund')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float('Quantity')
    location_id = fields.Many2one('stock.location', string='Restock Location')
    shopify_config_id = fields.Many2one("shopify.config",string="Shopify Configuration", related='refund_id.credit_note_id.shopify_config_id')
    shopify_line_id = fields.Char('Shopify Item Line')


class ShopifyExportRefund(models.TransientModel):
    _name = "shopify.export.refund"
    _description = "Export Shopify Refund"

    credit_note_id = fields.Many2one('account.move', string='Credit Note')
    restock_type = fields.Selection([('no_restock', 'No Restock'),
                                   # ('return', 'Return'),
                                   # ('cancel', 'Cancel')
                                     ], default='no_restock', string='Restock Type')
    refund_reason = fields.Text("Refund Reason")
    is_notify_customer = fields.Boolean('Notify Customer')
    total_refund_amount = fields.Float('Total Refund Amount')
    shipping_refund_amount = fields.Float('Shipping Refund Amount')
    currency_id = fields.Many2one('res.currency', string='Currency')
    refund_line_ids = fields.One2many('shopify.export.refund.line', 'refund_id', string='Refund Lines')
    order_shipping_amount = fields.Float(string='Shipping Amount in Order')
    no_lines = fields.Boolean('No Lines') #Boolean to display refund lines
    location_id = fields.Many2one('stock.location', string='Location')
    shopify_config_id = fields.Many2one("shopify.config",string="Shopify Configuration", related='credit_note_id.shopify_config_id')

    def prepare_shopify_refund_line_vals(self, credit_note_id):
        """ Prepares Refund Line Item values """
        shopify_refund_lines = []
        refund_orders = shopify.Refund.find(order_id=str(credit_note_id.shopify_order_id))
        for line in self.refund_line_ids:
            if line.shopify_line_id:
                total_refunded_qty = 0
                line_qty = 0
                line_quantity = int(line.quantity)
                for refund in refund_orders:
                    flag = False
                    for refund_line in refund.refund_line_items:
                        if str(refund_line.line_item_id) == line.shopify_line_id:
                            total_refunded_qty += refund_line.quantity
                            if not flag:
                                line_qty += refund_line.line_item.quantity
                if total_refunded_qty == line_qty:
                    continue
                remaining_qty = line_qty - total_refunded_qty
                if remaining_qty <= line_quantity:
                    line_quantity = remaining_qty
                if line_quantity != 0:
                    vals = {
                            'quantity': int(line.quantity),
                            'line_item_id': line.shopify_line_id,
                            'restock_type': self.restock_type,
                            }

                # If restock type is return then add return location
                if self.restock_type in ['return', 'cancel']: #add cancel in xml
                    if not line.location_id:
                        raise UserError(_("Location should not be empty. Select a Restock Location for the stock returned."))
                    mapping_location_id = self.env[
                        'shopify.location.mapping'].search(
                        [('odoo_location_id', '=', line.location_id.id),
                         ('shopify_config_id',
                          '=', self.shopify_config_id.id)
                         ], limit=1)
                    if not mapping_location_id:
                        raise UserError(_('Please select correct mapped location to return the product in shopify!!!'))
                    vals.update({'location_id': mapping_location_id.shopify_location_id})
                shopify_refund_lines.append(vals)
        return shopify_refund_lines

    def prepare_refund_vals(self, shopify_order_id, payment_details, refund_line_items, shipping={}):
        """ Prepares Refund values """
        transactions = []
        for parent_id, gateway in payment_details.items():
            transactions.append({
                "gateway": gateway[0],
                "parent_id": parent_id,
                "amount": gateway[1],
                "kind": "refund",
            })
        return {
                'order_id': shopify_order_id,
                'note': self.refund_reason,
                'notify': self.is_notify_customer,
                'shipping': shipping,
                'transactions': transactions,
                'refund_line_items': refund_line_items,
                }

    def check_refund_amount(self, shopify_order_id, order, refund_amount):
        """ This method checks whether refund amount of credit note is elligble for refund or not
        returns: parent id and gateway from transaction api response for kind 'sale'
        """
        transactions = shopify.Transaction().find(order_id=str(shopify_order_id))
        payment_details = {}
        total_paid_in_shopify = 0.0
        total_refund_in_shopify = 0.0
        # refund_to_allow = order.amount_total
        remaining_refund_amount = refund_amount

        refund_transactions = []
        for transaction in transactions:
            if transaction.kind == 'refund':
                refund_transactions.append(transaction)

        for transaction in transactions:
            if remaining_refund_amount == 0:
                continue
            transaction_data = transaction.to_dict()
            if transaction_data.get('kind') == 'sale':
                parent_id = transaction_data.get('id')
                gateway = transaction_data.get('gateway')

                transaction_amount = float(transaction_data.get(
                        'amount'))
                for refund_tran in refund_transactions:
                    if refund_tran.parent_id == transaction_data.get('id'):
                        transaction_amount = (transaction_amount -
                                              float(refund_tran.amount))

                if remaining_refund_amount <= transaction_amount:
                    transaction_amount = remaining_refund_amount
                    if transaction_amount > 0:
                        remaining_refund_amount = 0

                if remaining_refund_amount > transaction_amount:
                    remaining_refund_amount = (remaining_refund_amount -
                                               transaction_amount)

                payment_details.update({parent_id: [gateway, transaction_amount]})
                total_paid_in_shopify += float(transaction_data.get('amount'))
            if transaction_data.get('kind') == 'refund' and transaction_data.get('status') == 'success':
                total_refund_in_shopify += float(transaction_data.get('amount'))

        refund_to_allow = total_paid_in_shopify - (total_refund_in_shopify + refund_amount)
        allowed_refund = total_paid_in_shopify - total_refund_in_shopify
        if refund_to_allow < 0.0:
            raise UserError(_("Refund amount cannot be more than actual payment. Payment Amount is %s and Allowed refund amount is %s") %
                (order.amount_total, allowed_refund))
        return payment_details


    def refund_in_shopify(self):
        """
        Creates Refund in Shopify with below steps
        1. Prepares refund line data
        2. Check refund amount using transactions
        3. Prepares refund data
        4. Refund API call
        """
        shopify_order_id = self.credit_note_id.shopify_order_id
        if shopify_order_id:
            shopify_log_line_obj = self.env['shopify.log.line']
            order_id = self.credit_note_id.sale_order_id
            shopify_config = self.credit_note_id.shopify_config_id

            log_line_vals = {
                'name': "Export Refunds",
                'shopify_config_id': shopify_config.id,
                'operation_type': 'export_refund',
            }
            parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

            name = order_id.name or ''
            job_descr = (_("Export Refund from Odoo to shopify for Order : %s")
                         % (
                    name and name.strip()))
            log_line_id = shopify_log_line_obj.create({
                'name': job_descr,
                'shopify_config_id': shopify_config.id,
                'id_shopify': shopify_order_id,
                'operation_type': 'export_refund',
                'parent_id': parent_log_line_id.id
            })
            try:
                eta = datetime.now() + timedelta(seconds=2)
                self.with_delay(
                        description=job_descr, max_retries=5,
                        eta=eta).refund_in_shopify_queue(shopify_order_id, log_line_id)
            except Exception as e:
                error_message = "Refund export operation have following " \
                                    "error %s" % e
                log_line_id.write({'state': 'error',
                                   'message': error_message})
            parent_log_line_id.update({
                'state': 'success',
                'message': 'Operation Successful'
            })

    def refund_in_shopify_queue(self, shopify_order_id, log_line_id):
        """
        Creates Refund in Shopify with below steps
        1. Prepares refund line data
        2. Check refund amount using transactions
        3. Prepares refund data
        4. Refund API call
        """
        if shopify_order_id:
            shipping = {}
            order_id = self.credit_note_id.sale_order_id
            shopify_config = self.credit_note_id.shopify_config_id
            shopify_config.check_connection()
            refund_line_items = self.prepare_shopify_refund_line_vals(self.credit_note_id)
            # TODO: confirm with team about shipping refund
            # compare amt with same order amt for shipping product
            if self.shipping_refund_amount and self.order_shipping_amount:
                shipping.update({"full_refund": True})
            else:
                shipping.update({'amount': self.shipping_refund_amount})
            payment_details = self.check_refund_amount(shopify_order_id,
                                                     order_id, self.total_refund_amount
                )
            try:
                if payment_details:
                    refund_vals = self.prepare_refund_vals(shopify_order_id,
                                                           payment_details,
                                                           refund_line_items, shipping=shipping)
                    shopify_refund = shopify.Refund()
                    shopify_refund_response = shopify_refund.create(refund_vals)
                    response = shopify_refund_response.to_dict()
                    self.credit_note_id.update({
                        'shopify_transaction_id': response.get('id')
                    })
                    if log_line_id:
                        log_line_id.write({'state': 'success'})
            except Exception as e:
                error_message = "Refund export operation have following " \
                                    "error %s" % e
                if log_line_id:
                    log_line_id.write({'state': 'error',
                                       'message': error_message})
                raise UserError(_(error_message))

