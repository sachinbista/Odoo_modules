##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo.exceptions import UserError, ValidationError
import logging
from odoo import models, fields, api, _
from itertools import groupby
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import json
import time
from .. import shopify

_logger = logging.getLogger(__name__)


# class StockInventory(models.Model):
#     _inherit = "stock.inventory"

#     shopify_adjustment = fields.Boolean("Shopify Adjustment")

class StockMove(models.Model):
    _inherit = "stock.move"

    shopify_adjustment = fields.Boolean("Shopify Adjustment")

    # def _action_done(self, cancel_backorder=False):
    #     qty = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
    #     if self.picking_id and self.picking_id.picking_type_id.code =='internal':
    #         shopify_picking = False
    #         if self.picking_id.sale_id:
    #             if self.picking_id.sale_id.shopify_order_id:
    #                 shopify_picking = True
    #         if not shopify_picking:
    #             error_log_env = self.env['shopify.error.log']
    #             shopify_log_line_dict = {'error': [], 'success': []}
    #             product_lst = []
    #             for pro in self.product_id:
    #                 product_lst.append(pro.id)
    #             shopify_config = self.env['shopify.config'].sudo().search(
    #                 [('state', '=', 'success'), ('default_company_id', '=', self.picking_id.company_id.id)])
    #             shopify_config.sudo().check_connection()
    #             shopify_log_id = error_log_env.sudo().create_update_log(
    #                 shopify_config_id=shopify_config,
    #                 operation_type='export_stock')
    #             if shopify_config:
    #                 location_ids = self.env['stock.location'].search(
    #                     [('shopify_config_id', '=', shopify_config.id), ('usage', '=', 'view'),
    #                      ('shopify_location_id', '!=', False)])
    #                 if not location_ids:
    #                     log_message = "location not found for shopify config %s " % self.name
    #                     shopify_log_line_dict['error'].append(
    #                         {'error_message': 'Export STOCK: %s' % log_message})
    #                     return 0
    #                 shopify_variant_id = self.env['shopify.product.product'].sudo().search(
    #                     [('shopify_config_id', '=', shopify_config.id),
    #                      ('update_shopify_inv', '=', True), ('product_variant_id', 'in', product_lst)])
    #                 f_qty = 0.0
    #                 sh_location = ''
    #                 sh_inv_item = ''
    #                 product_variant_id = False
    #                 for location_id in location_ids:
    #                     for pp_variant in shopify_variant_id:
    #                         product_variant_id = pp_variant.product_variant_id
    #                         if product_variant_id.detailed_type == 'product' and not pp_variant.shopify_inventory_item_id:
    #                             log_message = "Inventory item ID not found for Product Variant %s in export stock." % product_variant_id.name
    #                             shopify_log_line_dict['error'].append(
    #                                 {'error_message': 'Export stock: %s' % log_message})
    #                             continue
    #                         # qty_available = product_variant_id.with_context(
    #                         #     {'location': location_id.id})._product_available()
    #                         if product_variant_id:
    #                             qty_available = product_variant_id.with_context(
    #                                 {'location': location_id.id})._compute_quantities_dict(self._context.get('lot_id'),
    #                                                                                        self._context.get(
    #                                                                                            'owner_id'),
    #                                                                                        self._context.get(
    #                                                                                            'package_id'))
    #                             variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
    #                             shopify_location_id = location_id.shopify_location_id
    #                             shopify_inventory_item_id = pp_variant.shopify_inventory_item_id
    #                             f_qty += variant_qty
    #                             sh_location = shopify_location_id
    #                             sh_inv_item = shopify_inventory_item_id
    #                 try:
    #                     shopify.InventoryLevel.set(sh_location,
    #                                                sh_inv_item,
    #                                                int(f_qty))
    #                     _logger.info(
    #                         'Export stock successfully for location "%s" inventory item id "%s" : %s' % (
    #                             sh_location, sh_inv_item, f_qty))
    #
    #                 except Exception as e:
    #                     if e.code == 429:
    #                         time.sleep(5)
    #                         shopify_config.InventoryLevel.set(sh_location,
    #                                                           sh_inv_item,
    #                                                           int(f_qty))
    #                     else:
    #                         if product_variant_id:
    #                             log_message = "Facing a problem while exporting Stock for shopify product variant %s: %s" % (
    #                                 product_variant_id.display_name, str(e))
    #                             shopify_log_line_dict['error'].append(
    #                                 {'error_message': 'Export stock: %s' % log_message})
    #                         else:
    #                             pass
    #             shopify_config.sudo().write({'last_stock_export_date': fields.Datetime.now()})
    #             error_log_env.create_update_log(shopify_config_id=shopify_config,
    #                                             shop_error_log_id=shopify_log_id,
    #                                             shopify_log_line_dict=shopify_log_line_dict)
    #     return qty

    # def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
    #                               owner_id=None,
    #                               strict=True):
    #     taken_quantity = super(StockMove, self)._update_reserved_quantity(need=need,
    #                                                                       available_quantity=available_quantity,
    #                                                                       location_id=location_id, lot_id=lot_id,
    #                                                                       package_id=package_id, owner_id=owner_id,
    #                                                                       strict=strict)
    #     if self.picking_id and self.picking_id.picking_type_id.code in [
    #         'outgoing', 'internal']:
    #         shopify_picking = False
    #         if self.picking_id.sale_id:
    #             if self.picking_id.sale_id.shopify_order_id:
    #                 shopify_picking = True
    #         if not shopify_picking:
    #             error_log_env = self.env['shopify.error.log']
    #             shopify_log_line_dict = {'error': [], 'success': []}
    #             product_id = self.product_id.id
    #             shopify_config = self.env['shopify.config'].sudo().search(
    #                 [('state', '=', 'success'), ('default_company_id', '=', self.picking_id.company_id.id)])
    #             shopify_config.sudo().check_connection()
    #             shopify_log_id = error_log_env.sudo().create_update_log(
    #                 shopify_config_id=shopify_config,
    #                 operation_type='export_stock')
    #             if shopify_config:
    #                 location_ids = self.env['stock.location'].search(
    #                     [('shopify_config_id', '=', shopify_config.id), ('usage', '=', 'view'),
    #                      ('shopify_location_id', '!=', False)])
    #                 if not location_ids:
    #                     log_message = "location not found for shopify config %s " % self.name
    #                     shopify_log_line_dict['error'].append(
    #                         {'error_message': 'Export STOCK: %s' % log_message})
    #                     return 0
    #                 shopify_variant_id = self.env['shopify.product.product'].sudo().search(
    #                     [('shopify_config_id', '=', shopify_config.id),
    #                      ('update_shopify_inv', '=', True), ('product_variant_id', '=', product_id)])
    #                 f_qty = 0.0
    #                 sh_location = ''
    #                 sh_inv_item = ''
    #
    #                 for location_id in location_ids:
    #                     if not location_ids:
    #                         log_message = "Location not found for shopify config %s " % self.name
    #                         shopify_log_line_dict['error'].append(
    #                             {'error_message': 'Export stock: %s' % log_message})
    #                         return 0
    #                     product_variant_id = shopify_variant_id.product_variant_id
    #                     if product_variant_id.detailed_type == 'product' and not shopify_variant_id.shopify_inventory_item_id:
    #                         log_message = "Inventory item ID not found for Product Variant %s in export stock." % product_variant_id.name
    #                         shopify_log_line_dict['error'].append(
    #                             {'error_message': 'Export stock: %s' % log_message})
    #                         continue
    #                     # qty_available = product_variant_id.with_context(
    #                     #     {'location': location_id.id})._product_available()
    #                     if product_variant_id:
    #                         qty_available = product_variant_id.with_context(
    #                             {'location': location_id.id})._compute_quantities_dict(self._context.get('lot_id'),
    #                                                                                    self._context.get('owner_id'),
    #                                                                                    self._context.get('package_id'))
    #                         variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
    #                         shopify_location_id = location_id.shopify_location_id
    #                         shopify_inventory_item_id = shopify_variant_id.shopify_inventory_item_id
    #                         f_qty += variant_qty
    #                         sh_location = shopify_location_id
    #                         sh_inv_item = shopify_inventory_item_id
    #                 try:
    #                     shopify.InventoryLevel.set(sh_location,
    #                                                sh_inv_item,
    #                                                int(f_qty))
    #                     _logger.info(
    #                         'Export stock successfully for location "%s" inventory item id "%s" : %s' % (
    #                             sh_location, sh_inv_item, f_qty))
    #
    #                 except Exception as e:
    #                     if e.code == 429:
    #                         time.sleep(5)
    #                         shopify_config.InventoryLevel.set(sh_location,
    #                                                           sh_inv_item,
    #                                                           int(f_qty))
    #                     else:
    #                         log_message = "Facing a problem while exporting Stock for shopify product variant %s: %s" % (
    #                             shopify_variant_id.display_name, str(e))
    #                         shopify_log_line_dict['error'].append(
    #                             {'error_message': 'Export stock: %s' % log_message})
    #             # shopify_config.last_stock_export_date = fields.Datetime.now()
    #             shopify_config.sudo().write({'last_stock_export_date': fields.Datetime.now()})
    #             error_log_env.create_update_log(shopify_config_id=shopify_config,
    #                                             shop_error_log_id=shopify_log_id,
    #                                             shopify_log_line_dict=shopify_log_line_dict)
    #             # if not shopify_log_id.shop_error_log_line_ids:
    #             #     shopify_log_id.unlink()
    #     return taken_quantity
    #
    # def _do_unreserve(self):
    #     move_reserve_dict = []
    #     for st_move in self:
    #         if st_move.picking_id and st_move.picking_id.picking_type_id.code in ['outgoing', 'internal']:
    #             if st_move.state == 'cancel' or (st_move.state == 'done' and st_move.scrapped):
    #                 continue
    #             else:
    #                 move_reserve_dict.append({'product_id': st_move.product_id,
    #                                           'location_id': st_move.location_id,
    #                                           'reserve_qry': st_move.reserved_availability})
    #     res = super(StockMove, self)._do_unreserve()
    #     for move in move_reserve_dict:
    #         shopify_picking = False
    #         for picking in self.picking_id:
    #             if picking.sale_id.shopify_order_id:
    #                 shopify_picking = True
    #         if not shopify_picking:
    #             error_log_env = self.env['shopify.error.log']
    #             shopify_log_line_dict = {'error': [], 'success': []}
    #             product_lst = []
    #             for pro in self.product_id:
    #                 product_lst.append(pro.id)
    #             # product_id = self.product_id.id
    #             shopify_config = self.env['shopify.config'].sudo().search(
    #                 [('state', '=', 'success'), ('default_company_id', '=', self.picking_id.company_id.id)])
    #             shopify_config.sudo().check_connection()
    #             shopify_log_id = error_log_env.sudo().create_update_log(
    #                 shopify_config_id=shopify_config,
    #                 operation_type='export_stock')
    #             if shopify_config:
    #                 location_ids = self.env['stock.location'].search(
    #                     [('shopify_config_id', '=', shopify_config.id), ('usage', '=', 'view'),
    #                      ('shopify_location_id', '!=', False)])
    #                 if not location_ids:
    #                     log_message = "location not found for shopify config %s " % st_move.name
    #                     shopify_log_line_dict['error'].append(
    #                         {'error_message': 'Export STOCK: %s' % log_message})
    #                     return False
    #                 shopify_variant_id = self.env['shopify.product.product'].sudo().search(
    #                     [('shopify_config_id', '=', shopify_config.id),
    #                      ('update_shopify_inv', '=', True), ('product_variant_id', 'in', product_lst)])
    #                 f_qty = 0.0
    #                 sh_location = ''
    #                 sh_inv_item = ''
    #                 product_variant_id = False
    #                 for location_id in location_ids:
    #                     for pp_variant in shopify_variant_id:
    #                         product_variant_id = pp_variant.product_variant_id
    #                         if product_variant_id.detailed_type == 'product' and not pp_variant.shopify_inventory_item_id:
    #                             log_message = "Inventory item ID not found for Product Variant %s in export stock." % product_variant_id.name
    #                             shopify_log_line_dict['error'].append(
    #                                 {'error_message': 'Export stock: %s' % log_message})
    #                             continue
    #                         # qty_available = product_variant_id.with_context(
    #                         #     {'location': location_id.id})._product_available()
    #                         if product_variant_id:
    #                             qty_available = product_variant_id.with_context(
    #                                 {'location': location_id.id})._compute_quantities_dict(self._context.get('lot_id'),
    #                                                                                        self._context.get('owner_id'),
    #                                                                                        self._context.get('package_id'))
    #                             variant_qty = qty_available[product_variant_id.id]['free_qty'] or 0.0
    #                             shopify_location_id = location_id.shopify_location_id
    #                             shopify_inventory_item_id = pp_variant.shopify_inventory_item_id
    #                             f_qty += variant_qty
    #                             sh_location = shopify_location_id
    #                             sh_inv_item = shopify_inventory_item_id
    #                 try:
    #                     shopify.InventoryLevel.set(sh_location,
    #                                                sh_inv_item,
    #                                                int(f_qty))
    #                     _logger.info(
    #                         'Export stock successfully for location "%s" inventory item id "%s" : %s' % (
    #                             sh_location, sh_inv_item, f_qty))
    #
    #                 except Exception as e:
    #                     if e.code == 429:
    #                         time.sleep(5)
    #                         shopify_config.InventoryLevel.set(sh_location,
    #                                                           sh_inv_item,
    #                                                           int(f_qty))
    #                     else:
    #                         if product_variant_id:
    #                             log_message = "Facing a problem while exporting Stock for shopify product variant %s: %s" % (
    #                                 product_variant_id.display_name, str(e))
    #                             shopify_log_line_dict['error'].append(
    #                                 {'error_message': 'Export stock: %s' % log_message})
    #                             continue
    #                         else:
    #                             continue
    #             shopify_config.sudo().write({'last_stock_export_date': fields.Datetime.now()})
    #             error_log_env.create_update_log(shopify_config_id=shopify_config,
    #                                             shop_error_log_id=shopify_log_id,
    #                                             shopify_log_line_dict=shopify_log_line_dict)
    #
    #     return res


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, out=False):
        res = super(StockQuant, self)._get_inventory_move_values(
            qty, location_id, location_dest_id, out=out)
        if self._context.get('shopify_adjustment'):
            res.update(
                {'shopify_adjustment': self._context.get('shopify_adjustment')})
        return res


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
        readonly=True)
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

    def _create_backorder(self):
        res = super(StockPicking, self)._create_backorder()
        if self.shopify_config_id:
            res.write({'shopify_config_id': self.shopify_config_id.id})
        return res

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        if not self._context.get('shopify_picking_validate'):
            shopify_picking_ids = self.filtered(lambda r: r.shopify_config_id and not r.is_updated_in_shopify
                                                          and r.location_dest_id.usage == 'customer' and r.state == 'done')
            if shopify_picking_ids:
                for picking in shopify_picking_ids:
                    # is_updated = self.env['sale.order'].shopify_update_order_status(
                    #     picking.shopify_config_id, picking_ids=picking)
                    shopify_config_id = picking.shopify_config_id
                    if shopify_config_id.is_auto_invoice_paid:
                        invoices = picking.sale_id.invoice_ids.filtered(
                            lambda
                                iv: iv.move_type == 'out_invoice' and iv.payment_state != 'paid' and iv.state != 'cancel')
                        if invoices.amount_total != picking.sale_id.amount_total:
                            self.sale_id.create_shopify_invoice(
                                shopify_config_id)
        return res


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    shopify_error_log = fields.Text(
        "Shopify Error",
        help="Error occurs while exporting move to the shopify",
        readonly=True)
    shopify_export = fields.Boolean(
        "Shopify Export", readonly=True)
    sale_line_id = fields.Many2one(
        related='move_id.sale_line_id', string='Sale Line')

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


class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.valuation.layer'

    @api.model_create_multi
    def create(self, vals):
        """
        :param vals: update date based move done date
        :return: recordset
        """
        for val in vals:
            rec = super(StockValuationLayer, self).create(val)
            if rec.stock_move_id:
                self.env.cr.execute(
                    """UPDATE stock_valuation_layer SET create_date = %(date)s 
                        WHERE id = %(rec_id)s""",
                    {'date': rec.stock_move_id.date,
                     'rec_id': rec.id})
            return rec
