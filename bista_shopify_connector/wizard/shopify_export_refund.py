##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
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
                                   ('return', 'Return'),
                                   ('cancel', 'Cancel')], default='no_restock', string='Restock Type')
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
        """
            Prepares Refund Line Item values.
            @return : shopify_refund_lines
            @author: Pooja Zankhariya @Bista Solutions Pvt. Ltd.
        """
        shopify_refund_lines = []
        for line in self.refund_line_ids:
            vals = {
                    'quantity': int(line.quantity),
                    'line_item_id': line.shopify_line_id,
                    'restock_type': self.restock_type,
                    }
            # If restock type is return then add return location
            if self.restock_type in ['return', 'cancel']: #add cancel in xml
                if not line.location_id:
                    raise UserError(_("Location should not be empty. Select a Restock Location for the stock returned."))
                vals.update({'location_id': line.location_id.shopify_location_id})
            shopify_refund_lines.append(vals)
        return shopify_refund_lines

    def prepare_refund_vals(self, shopify_order_id, gateway, parent_id, refund_line_items, shipping={}):
        """
            Prepares Refund values.
            @author: Pooja Zankhariya @Bista Solutions Pvt. Ltd.
        """
        return {
                'order_id': shopify_order_id,
                'note': self.refund_reason,
                'notify': self.is_notify_customer,
                'shipping': shipping,
                'transactions': [{
                                "gateway": gateway,
                                "parent_id": parent_id,
                                "amount": self.total_refund_amount,
                                "kind": "refund",
                                }],
                'refund_line_items': refund_line_items,
                }

    def check_refund_amount(self, shopify_order_id, order, refund_amount):
        """
            This method checks whether refund amount of credit note is elligble for refund or not
            returns: parent id and gateway from transaction api response for kind 'sale'
            @author: Pooja Zankhariya @Bista Solutions Pvt. Ltd.
         """
        transactions = shopify.Transaction().find(order_id=str(shopify_order_id))
        parent_id = False
        gateway = False
        total_refund_in_shopify = 0.0
        refund_to_allow = order.amount_total
        for transaction in transactions:
            transaction_data = transaction.to_dict()
            if transaction_data.get('kind') == 'sale':
                parent_id = transaction_data.get('id')
                gateway = transaction_data.get('gateway')
            if transaction_data.get('kind') == 'refund' and transaction_data.get('status') == 'success':
                total_refund_in_shopify += float(transaction_data.get('amount'))
        refund_to_allow = refund_to_allow - total_refund_in_shopify - refund_amount
        allowed_refund = order.amount_total - total_refund_in_shopify
        if refund_to_allow < 0.0:
            raise UserError(_("Refund amount cannot be more than actual payment. Payment Amount is %s and Allowed refund amount is %s") % 
                (order.amount_total, allowed_refund))
        return parent_id, gateway

    def refund_in_shopify(self):
        """
            Creates Refund in Shopify with below steps
            1. Prepares refund line data
            2. Check refund amount using transactions
            3. Prepares refund data
            4. Refund API call
            @author: Pooja Zankhariya @Bista Solutions Pvt. Ltd.
        """
        shopify_order_id = self.credit_note_id.shopify_order_id
        if shopify_order_id:
            error_log_env = self.env['shopify.error.log'].sudo()
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
            # if self.shipping_refund_amount > 0.0:
            #     shipping.update({'amount': self.shipping_refund_amount})
            # else:
            #     shipping.update({"full_refund": True})
            parent_id, gateway = self.check_refund_amount(shopify_order_id, order_id, self.total_refund_amount
                )
            try:
                if parent_id and gateway:
                    self.credit_note_id.write({'is_manual_odoo_refund': True})
                    order_id.write({'is_manual_odoo_refund':True})
                    refund_vals = self.prepare_refund_vals(shopify_order_id, gateway, parent_id, refund_line_items, shipping=shipping)
                    shopify_refund = shopify.Refund()
                    shopify_refund_response = shopify_refund.create(refund_vals)
                    response = shopify_refund_response.to_dict()
                    self.credit_note_id.update({'shopify_transaction_id': response.get('id')})
            except Exception as e:
                error_message = "Refund export operation have following " \
                                    "error %s" % e
                shopify_log_id = error_log_env.sudo().create_update_log(
                                shopify_config_id=shopify_config,
                                operation_type='export_refund')
                error_log_env.sudo().create_update_log(
                            shop_error_log_id=shopify_log_id,
                            shopify_log_line_dict={'error': [
                                    {'error_message': error_message}]})

