##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import numpy as np
import pandas as pd
import requests
import json
from .. import shopify
import time
import threading
import logging
import re
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    shopify_adjustment = fields.Boolean("Shopify Adjustment")


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        res = super(StockQuant, self)._get_inventory_move_values(
            qty, location_id, location_dest_id, package_id, package_dest_id
        )
        if self._context.get('shopify_adjustment'):
            res.update(
                {'shopify_adjustment': self._context.get('shopify_adjustment')})
        return res

    @api.constrains('lot_id')
    def _constrains_lot_id(self):
        """
            Added the constraint to restrict the produt dont have lot or serial number.
        """
        for stock in self:
            if stock.tracking and stock.tracking in ['serial']:
                if not stock.lot_id:
                    raise UserError(
                        _('Please add "Serial Number" for product %s!') % stock.product_id.name)


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    shopify_fulfillment_id = fields.Char(
        "Shopify Fulfillment ID",
        help='Enter Shopify Fulfillment ID',
        readonly=True,
        copy=False)
    shopify_order_id = fields.Char(
        "Shopify Order ID",
        help='Enter Shopify Order ID',
        readonly=False)
    shopify_fulfillment_service = fields.Char("Fulfillment Service.",
                                              help="Shopify service name.",
                                              copy=False)
    shopify_config_id = fields.Many2one("shopify.config",
                                        string="Shopify Configuration",
                                        help="Enter Shopify Configuration",
                                        tracking=True,
                                        copy=False)
    shopify_hist_data = fields.Boolean('Shopify Historical Data', copy=False)
    refund_line_id = fields.Char("Shopify Line Id.", copy=False)
    shopify_shipment_status = fields.Char("Shopify Shipment Status")
    is_updated_in_shopify = fields.Boolean(
        string='Updated In Shopify?', copy=False, readonly=True, default=False)
    shopify_refund_id = fields.Char("Shopify Refund ID", copy=False)
    picking_return_id = fields.Many2one("stock.picking", string="Return Of")
    shopify_tracking_url = fields.Char(
        string='Shopify Tracking URL', tracking=True)
    shopify_order_number = fields.Char('Shopify Order Number', copy=False)
    shopify_transaction_id = fields.Char(string='Shopify Transaction ID',
                                         copy=False)
    fulfillment_status = fields.Char('Fulfillment Status', copy=False)

    def _create_backorder(self):
        """
            This method will create backorder and assign instance.
            @author: Yogeshwar Chaudhari @Bista Solutions Pvt. Ltd.
        """
        res = super(StockPicking, self)._create_backorder()
        if self.shopify_config_id:
            res.write({'shopify_config_id': self.shopify_config_id.id})
        return res

    def send_qty_shopify(
            self, shopify_config_rec, shopify_location_rec, product_id, qty
    ):
        """
            This method will send the qty to shopify to update.
            @author: Farid Ghanchi @Bista Solutions Pvt. Ltd.
        """
        shopify_log_id = False
        shopify_prod_obj = self.env["shopify.product.product"]
        shopify_config_rec.check_connection()
        shopify_product = shopify_prod_obj.with_user(self.env.user).search(
            [
                ("product_variant_id", "=", product_id.id),
                ("shopify_config_id", "=", shopify_config_rec.id),
                ("update_shopify_inv", "=", True),
            ],
            limit=1,
        )
        if shopify_product:
            shopify_location_id = shopify_location_rec  # .shopify_location_id
            inventory_item_id = shopify_product.shopify_inventory_item_id
            if inventory_item_id:
                shopify_config_rec.with_user(self.env.user).update_shopify_inventory(
                    shopify_location_id, inventory_item_id, int(qty), shopify_log_id
                )
        return True

    def do_unreserve(self):
        """
            This method will send the qty to shopify to update on unreserve.
            @author: Farid Ghanchi @Bista Solutions Pvt. Ltd.
        """
        res = super(StockPicking, self).do_unreserve()
        if (self.shopify_config_id and self.shopify_config_id.is_stock_update_reservation):
            self.prepare_stock_details_for_shopify(self)
        return res

    def prepare_stock_details_for_shopify(self, pickings):
        """
            This method will prepare the stock details to update at shopify.
            @author: Farid Ghanchi @Bista Solutions Pvt. Ltd.
        """
        for picking_id in pickings.filtered(
                lambda x: x.picking_type_id.code in ("outgoing", "internal")
                          and (
                                  x.location_id.shopify_location_id
                                  or x.location_dest_id.shopify_location_id
                          )
        ):
            for move in picking_id.move_ids:
                product_id = move.product_id
                qty = product_id.with_context(
                    location=picking_id.location_id.id
                ).free_qty
                if move.location_id.shopify_location_id:
                    shopify_location_rec = move.location_id.shopify_location_id
                    shopify_config_rec = move.location_id.shopify_config_id
                else:
                    shopify_location_rec = move.location_dest_id.shopify_location_id
                    shopify_config_rec = move.location_dest_id.shopify_config_id
                if shopify_location_rec:
                    self.send_qty_shopify(
                        shopify_config_rec, shopify_location_rec, product_id, qty
                    )

    def action_assign(self):
        """
            Check availability of picking moves.
            This has the effect of changing the state and reserve quants on available moves, and may
            also impact the state of the picking as it is computed based on move's states.
            @return: True
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        res = super(StockPicking, self).action_assign()
        if (
                self.shopify_config_id
                and self.shopify_config_id.is_stock_update_reservation
        ):
            self.prepare_stock_details_for_shopify(self)
        return res

    def action_confirm(self):
        """
            Check availability of picking moves.
            This has the effect of changing the state and reserve quants on available moves, and may
            also impact the state of the picking as it is computed based on move's states.
            @return: True
            @author: Nupur Soni @Bista Solutions Pvt. Ltd.
        """
        res = super(StockPicking, self).action_confirm()
        if (
                self.shopify_config_id
                and self.shopify_config_id.is_stock_update_reservation
        ):
            self.prepare_stock_details_for_shopify(self)
        return res

    def _action_done(self):
        """
            This method will call on done and create invoices.
            @author: Niva Nirmal @Bista Solutions Pvt. Ltd.
        """
        res = super(StockPicking, self)._action_done()
        if not self._context.get('shopify_picking_validate'):
            shopify_picking_ids = self.filtered(
                lambda r: r.shopify_config_id and not r.is_updated_in_shopify and
                r.location_dest_id.usage == 'customer' and r.state == 'done'
            )
            if shopify_picking_ids:
                for picking in shopify_picking_ids:
                    is_updated = self.env['sale.order'].sudo().shopify_update_order_status(
                        picking.shopify_config_id, picking_ids=picking)
                    shopify_config_id = picking.shopify_config_id
                    if shopify_config_id.is_auto_invoice_paid:
                        invoices = picking.sale_id.invoice_ids.filtered(
                            lambda iv: iv.move_type == 'out_invoice' and iv.payment_state != 'paid' and iv.state != 'cancel')
                        if invoices.amount_total != picking.sale_id.amount_total:
                            self.sale_id.create_shopify_invoice(
                                shopify_config_id)
        return res

    def update_tracking_info(self):
        """
            Using this method updating the tracking information in shopify from odoo.
        """
        shopify_config = self.env['shopify.config']
        shopify_config_id = shopify_config.search(
            [('state', '=', 'success')], limit=1)
        token = shopify_config_id.password
        graphql_url = shopify_config_id.graphql_url
        user = self.env.user
        if not self.shopify_tracking_url:
            raise UserError(
                _("Tracking URL is missing, Please enter a Tracking URL."))
        if not self.carrier_id:
            raise UserError(
                _("Carrier (Company) is missing, Please enter a Carrier."))
        if not self.carrier_tracking_ref:
            raise UserError(
                _("Traking number is missing, Please enter a Tracking Number."))
        if not self.shopify_fulfillment_id:
            raise UserError(
                _("Shopify Fullfillment ID is missing, Please check."))
        if not graphql_url:
            raise UserError(
                _("GraphQL URL is missing, Please enter a GraphQL URL"))
        if not token:
            raise UserError(_("Access token is missing, Please check."))

        s_tracking_url = self.is_valid_url(self.shopify_tracking_url)

        if s_tracking_url is False:
            raise UserError(_("Please enter valid Tracking URL."))
        try:
            url, access_token = graphql_url, token

            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token
            }

            mutation = """ mutation fulfillmentTrackingInfoUpdateV2($fulfillmentId: ID!, $trackingInfoInput: FulfillmentTrackingInput!, $notifyCustomer: Boolean) {
                fulfillmentTrackingInfoUpdateV2(fulfillmentId: $fulfillmentId, trackingInfoInput: $trackingInfoInput, notifyCustomer: $notifyCustomer) {
                fulfillment {
                    id
                    status
                    trackingInfo {
                        company
                        number
                        url
                    }
                }
                userErrors {
                    field
                    message
                }
                }
                }
            """
            variables = {
                "fulfillmentId": "gid://shopify/Fulfillment/"+self.shopify_fulfillment_id,
                "notifyCustomer": True,
                "trackingInfoInput": {
                    "company": self.carrier_id.name,
                    "number": self.carrier_tracking_ref,
                    "url": self.shopify_tracking_url,
                }
            }
            try:
                data = {"query": mutation, "variables": variables}
                response = requests.post(
                    url, headers=headers, data=json.dumps(data), timeout=10)
                message = {
                    'Carrier': self.carrier_id.name,
                    'Tracking Number': self.carrier_tracking_ref,
                    'URL': self.shopify_tracking_url
                }
                updated_fields = str(message)[1:-1]
                self.message_post(body=f"Tracking information is updated in shopify by {user.name}, {updated_fields}.")
                _logger.info(response)
            except Exception as e:
                raise UserError(e)
        except Exception as e:
            raise UserError(e)

    def is_valid_url(self, url):
        """
        Regular expression to validate a URL
        """
        url_pattern = re.compile(
            r'^(https?://)?'
            r'([a-zA-Z0-9.-]+)'
            r'(\.[a-zA-Z]{2,4})'
            r'(/[-a-zA-Z0-9_.]*)*'
            r'(\?[a-zA-Z0-9_=&]*)?'
            r'(#[-a-zA-Z0-9_]*)?$'
        )
        return bool(url_pattern.match(url))


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.depends('picking_id')
    def binding_lot_ids(self):
        """
            Binding the lot/serial number to the return from outgoing delivery order.
        """
        stockmove = self.env['stock.move']
        stockmoveline = self.env['stock.move.line']
        lot_list = []
        for order in self:
            order.lot_ids = []
            if order.picking_id.picking_return_id:
                picking_id = order.picking_id.picking_return_id
                stock_move_ids = stockmove.search(
                    [('picking_id', '=', picking_id.id)])
                if stock_move_ids:
                    for move_id in stock_move_ids:
                        stock_move_line = stockmoveline.search(
                            [('move_id', '=', move_id.id)])
                        for move_line in stock_move_line:
                            lot_list.append(move_line.lot_id.id)
            else:
                all_lots = self.env['stock.lot'].search(
                    [('product_id', '=', order.product_id.id)])
                lot_list = all_lots.ids
            order.lot_ids = lot_list

    shopify_error_log = fields.Text(
        "Shopify Error",
        help="Error occurs while exporting move to the shopify",
        readonly=True)
    shopify_export = fields.Boolean(
        "Shopify Export", readonly=True)
    sale_line_id = fields.Many2one(
        related='move_id.sale_line_id', string='Sale Line')
    lot_ids = fields.Many2many("stock.lot", compute="binding_lot_ids")

    def _check_location_config(self, location_id, location_dest_id):
        """
        TODO : Check usage
        Warning raise if account are wrongly configured in locations
        'Cannot create moves for different companies.'
        till that time shopify call is executed. To avoid this
        function will try to access configure accounts and it's company
        """
        if location_id:
            valuation_in_account_id = location_id.valuation_in_account_id
            if valuation_in_account_id:
                location_company_id = valuation_in_account_id.company_id
        if location_dest_id:
            valuation_out_account_id = \
                location_dest_id.valuation_out_account_id
            if valuation_out_account_id:
                location_dest_company_id = valuation_out_account_id.company_id

    def _action_done(self):
        """
            this method override for update shopify stock
            :return:
            @author: Farid Ghanchi @Bista Solutions Pvt. Ltd.
        """
        # Avoid updating inv in shopify at the time of import stock
        res = super(StockMoveLine, self)._action_done()
        shopify_line_ids = self.filtered(
            lambda s: s.location_id.shopify_location_id
                      or s.location_dest_id.shopify_location_id
        )

        for line in shopify_line_ids:
            if (
                    line.location_id.shopify_location_id
                    and line.location_id.shopify_config_id
            ):
                shopify_location_id = line.location_id.shopify_location_id
                shopify_config_rec = line.location_id.shopify_config_id
                # qty = line.qty_done * -1
                qty = line.product_id.with_context(
                    location=line.location_id.id
                ).free_qty
                line.send_quantity_to_shopify(
                    shopify_config_rec, shopify_location_id, qty
                )
            if (
                    line.location_dest_id.shopify_location_id
                    and line.location_dest_id.shopify_config_id
            ):
                shopify_location_id = line.location_dest_id.shopify_location_id
                shopify_config_rec = line.location_dest_id.shopify_config_id
                # qty = line.qty_done
                qty = line.product_id.with_context(
                    location=line.location_dest_id.id
                ).free_qty
                line.send_quantity_to_shopify(
                    shopify_config_rec, shopify_location_id, qty
                )
        return res

    def send_quantity_to_shopify(self, shopify_config_rec, shopify_location_id, qty):
        shopify_config_rec.check_connection()
        shopify_prod_obj = self.env["shopify.product.product"]
        shopify_product = shopify_prod_obj.with_user(self.env.user).search(
            [
                ("product_variant_id", "=", self.product_id.id),
                ("shopify_config_id", "=", shopify_config_rec.id),
            ],
            limit=1,
        )
        if shopify_product:
            inventory_item_id = shopify_product.shopify_inventory_item_id
            shopify_log_id = False
            if inventory_item_id:
                shopify_config_rec.with_user(self.env.user).update_shopify_inventory(
                    shopify_location_id, inventory_item_id, int(qty), shopify_log_id
                )

    def split_graphql_data_into_batches(self, input_list, batch_size):
        """
            Using this method spliting the bunch of data in chunks/batches
        """
        for data in range(0, len(input_list), batch_size):
            yield input_list[data:data + batch_size]


class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.valuation.layer'

    @api.model_create_multi
    def create(self, vals):
        """
        :param vals: update date based move done date
        :return: recordset
        """
        record = super(StockValuationLayer, self).create(vals)
        for rec in record:
            if rec.stock_move_id:
                self.env.cr.execute(
                    """UPDATE stock_valuation_layer SET create_date = %(date)s
                        WHERE id = %(rec_id)s""",
                    {'date': rec.stock_move_id.date,
                     'rec_id': rec.id})
        return record
