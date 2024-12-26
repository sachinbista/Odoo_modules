##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import logging
from odoo import models, fields, api, _
import requests
import json
import traceback
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = "stock.move"

    shopify_adjustment = fields.Boolean("Shopify Adjustment")
    shopify_item_line_id = fields.Char('Shopify Order Item Line ID', copy=False)
    shopify_assigned_location_id = fields.Char('Shopify Assigned Location ID',
                                               copy=False)
    shopify_fulfillment_order_id = fields.Char('Shopify Fulfillment Order ID')
    shopify_fulfillment_line_id = fields.Char('Shopify Fulfillment Line ID')

    def _prepare_move_split_vals(self, qty):
        '''Method inherit to update the shopify fields value on split'''
        vals = super(StockMove, self)._prepare_move_split_vals(qty)
        if self.picking_id and self.picking_id.shopify_config_id:
            vals.update({'shopify_item_line_id': self.shopify_item_line_id,
                         'shopify_assigned_location_id': self.shopify_assigned_location_id})
        return vals

    def write(self, vals):
        '''Method to only update location in shopify order when location is
        changed into pickings'''
        move_request_dict = []
        if vals.get('location_id') and not self._context.get(
                'move_update_from_fulfillment'):
            for each in self.filtered(
                    lambda m: m.picking_id and
                              m.picking_id.picking_type_id.code in (
                                      'outgoing')):
                if (each.picking_id.sale_id and
                        each.picking_id.sale_id.shopify_order_id and
                        each.location_id.id != vals.get('location_id')):

                    shopify_config = each.picking_id.sale_id.shopify_config_id
                    location_mapping_id = self.env[
                        'shopify.location.mapping'].search([
                            ('odoo_location_id', '=', vals['location_id']),
                            ('shopify_config_id', '=', shopify_config.id)],
                            limit=1)
                    if location_mapping_id:
                        headers = {
                            'X-Shopify-Access-Token':
                                each.picking_id.sale_id.shopify_config_id.password,
                            'Content-Type': 'application/json'}
                        sale_line_id = (
                            each.picking_id.sale_id.order_line.filtered(
                                lambda l: l.product_id.id == each.product_id.id
                                          and l.shopify_fulfillment_line_id)
                        )
                        url = shopify_config.shop_url
                        fulfillment_order_id = sale_line_id.shopify_fulfillment_order_id
                        api_order_url = ("/admin/api/2023-10/fulfillment_orders/%s/move.json") % (
                                            fulfillment_order_id)
                        url = url + api_order_url
                        if sale_line_id:
                            body = {"fulfillment_order": {
                                "new_location_id": location_mapping_id.shopify_location_id,
                                "fulfillment_order_line_items": [{
                                    'id': sale_line_id.shopify_fulfillment_line_id,
                                     'quantity': int(each.product_uom_qty)}]}}
                            if body:
                                move_request_dict.append({
                                    'url': url, 'data': body,
                                    'headers': headers, 'move_id': each})
        res = super(StockMove, self).write(vals)
        for move_req in move_request_dict:
            try:
                response = requests.request('POST', move_req.get('url'),
                                            headers=move_req.get('headers'),
                                            data=json.dumps(move_req.get('data')))
                fulfillment_dict = response.json()
                if fulfillment_dict.get('moved_fulfillment_order'):
                    shopify_fulfillment_order_id = fulfillment_dict.get(
                        'moved_fulfillment_order').get('id')
                    line_items =  fulfillment_dict.get(
                        'moved_fulfillment_order').get('line_items')
                    shopify_fulfillment_line_id = line_items[0].get('id')
                    if shopify_fulfillment_order_id \
                            and shopify_fulfillment_line_id:
                        ctx = dict(self._context) or {}
                        ctx.update({'move_update_from_fulfillment': True})
                        move_req.get('move_id').with_context(ctx).write({
                            'shopify_fulfillment_order_id':
                                        shopify_fulfillment_order_id,
                                    'shopify_fulfillment_line_id': shopify_fulfillment_line_id})
                if fulfillment_dict.get('errors'):
                    raise ValidationError(_(fulfillment_dict['errors']))
            except Exception as e:
                error_message = 'Error in updating location on shopify : {}'.format(
                    e)
                raise ValidationError(_(error_message))
        return res


    def _search_picking_for_assignation_domain(self):
        '''Method to help spliting of the picking'''
        if self.shopify_assigned_location_id:
            domain = [
                ('group_id', '=', self.group_id.id),
                #                 ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_dest_id.id),
                ('picking_type_id', '=', self.picking_type_id.id),
                ('printed', '=', False),
                # ('immediate_transfer', '=', False),
                ('state', 'in',
                 ['draft', 'confirmed', 'waiting', 'partially_available',
                  'assigned'])]
            if self.partner_id and (
                    self.location_id.usage == 'transit' or self.location_dest_id.usage == 'transit'):
                domain += [('partner_id', '=', self.partner_id.id)]
            return domain
        else:
            domain = [
                ('group_id', '=', self.group_id.id),
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_dest_id.id),
                ('picking_type_id', '=', self.picking_type_id.id),
                ('printed', '=', False),
                # ('immediate_transfer', '=', False),
                ('state', 'in',
                 ['draft', 'confirmed', 'waiting', 'partially_available',
                  'assigned'])]
            if self.partner_id and (
                    self.location_id.usage == 'transit' or self.location_dest_id.usage == 'transit'):
                domain += [('partner_id', '=', self.partner_id.id)]
            return domain

    def _verify_shopify_picking(self):
        shopify_picking = adjustment = False
        for move_line in self:
            if (move_line.picking_id.picking_type_id.code in [
                'outgoing', 'internal', 'incoming'] or move_line.reference
                    == 'Product Quantity Updated'):
                # exclude the method call if action done happening while shopify order
                if move_line.reference == 'Product Quantity Updated':
                    adjustment = True
                if not shopify_picking :
                    if not move_line.exists():
                        continue
                    if move_line.picking_id.sale_id:
                        if move_line.picking_id.sale_id.shopify_order_id:
                            shopify_picking = True
        return shopify_picking, adjustment

    def prepare_move_reserve_dict(self):
        '''Method to update reservation dictionary'''
        move_reserve_dict = []
        for move in self:
            if move.picking_id and move.picking_id.picking_type_id.code in ['outgoing', 'internal']:
                if move.state == 'cancel' or (move.state == 'done' and move.scrapped):
                    continue
                else:
                    move_reserve_dict.append({'product_id': move.product_id,
                                              'location_id': move.location_id,
                                              'reserve_qry': move.quantity})
        return move_reserve_dict

    def _do_unreserve_phantom_product_for_kit_products(self):
        return

    def _do_unreserve(self):
        move_reserve_dict = self.prepare_move_reserve_dict()
        res = super(StockMove, self)._do_unreserve()

        shopify_log_line_obj = self.env['shopify.log.line']
        log_line_vals = {
            'name': "Export Stock",
            'operation_type': 'export_stock',
        }
        parent_log_line_id = False
        shopify_initial_id = False

        shopify_picking, adjustment = self._verify_shopify_picking()
        for move in move_reserve_dict:
            # if not shopify_picking:
            shopify_prod_obj = self.env['shopify.product.product']
            try:
                taken_quantity = move.get('reserve_qry')
                if taken_quantity > 0:
                    location_id = self._check_if_child_location(move.get('location_id'))
                    location_mapping_ids = self.env[
                        'shopify.location.mapping'].search([
                        ('odoo_location_id', '=', location_id.id),
                        ('shopify_config_id.active', '=', True)])
                    shopify_location_recs = location_mapping_ids
                    for shopify_location_rec in shopify_location_recs:
                        if shopify_location_rec:
                                # shopify_location_rec.shopify_config_id.sync_inventory_on_reservation):
                            shopify_config_rec = shopify_location_rec.shopify_config_id
                            # shopify_config_rec.check_connection()
                            shopify_location_id = shopify_location_rec.shopify_location_id

                            shopify_product1 = shopify_prod_obj.with_user(
                                self.env.user).search([
                                ('product_variant_id', '=', move.get(
                                    'product_id').id),
                                ('shopify_config_id', '=',
                                 shopify_config_rec.id)], limit=1)
                            inventory_item_id = \
                                shopify_product1.shopify_inventory_item_id
                            # shopify_product_cost = product_rec.standard_price
                            if inventory_item_id and \
                                    shopify_product1.update_shopify_inv:
                                name = "%s - %s" % (
                                    shopify_location_rec.odoo_location_id.display_name,
                                    shopify_product1.product_variant_id.display_name)
                                if shopify_config_rec != shopify_initial_id:
                                    shopify_initial_id = shopify_config_rec
                                    log_line_vals.update({
                                        'shopify_config_id': shopify_config_rec.id,
                                    })
                                    parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                                job_descr = _(
                                    "Export Stock to shopify: %s") % (
                                                    name and name.strip())
                                log_line_id = shopify_log_line_obj.create(
                                    {
                                        'name': job_descr,
                                        'shopify_config_id': shopify_config_rec.id,
                                        'id_shopify': f"Location: "
                                                      f"{shopify_location_rec.shopify_location_id or ''} Inventory: {shopify_product1.shopify_inventory_item_id}",
                                        'operation_type': 'export_stock',
                                        'parent_id': parent_log_line_id.id
                                    })
                                qty = self.env['stock.quant']._get_quantity_with_child_locations(
                                    shopify_location_rec.odoo_location_id, shopify_product1.product_variant_id)
                                shopify_config_rec.with_user(
                                    self.env.user).with_company(shopify_config_rec.default_company_id).with_delay(
                                    description=job_descr,
                                    max_retries=5).update_shopify_inventory(
                                    shopify_location_id, inventory_item_id,
                                    int(qty), log_line_id)
                        if parent_log_line_id:
                            parent_log_line_id.update({
                                'state': 'success',
                                'message': 'Operation Successful'
                            })
            except Exception as e:
                parent_log_line_id.update({
                    'state': 'error',
                    'message': traceback.format_exc(),
                })
        # phantom product quantity update over the fix on inventory unreserve
        self._do_unreserve_phantom_product_for_kit_products()
        return res



    def _check_if_child_location(self, move_location_id):
        parent_id = move_location_id.location_id if move_location_id.location_id.usage == 'internal' else move_location_id
        while parent_id and parent_id.usage == 'internal':
            if parent_id.location_id.usage != 'internal':
                break
            parent_id = parent_id.location_id
        shopify_odoo_location_ids = self.env[
            'shopify.location.mapping'].search([
            ('shopify_config_id.active', '=', True)]).mapped('odoo_location_id')
        all_locations = self.env['stock.location'].search(
            [('id', 'child_of', parent_id.id)]).ids
        for odoo_location in shopify_odoo_location_ids:
            if odoo_location.id in all_locations:
                return odoo_location
        return move_location_id

    def check_product_creditibility(self):
        '''Method added to extended into shopify-roaster extend module'''
        return self.product_id

    def _update_phantom_reserved_quantity_for_kit_products(self):
        return

    def _update_reserved_quantity(self, need, location_id, quant_ids=None, lot_id=None, package_id=None, owner_id=None, strict=True):
        taken_quantity = super(StockMove, self)._update_reserved_quantity(
            need=need, location_id=location_id, quant_ids=quant_ids, lot_id=lot_id, package_id=package_id,
            owner_id=owner_id, strict=strict)
        self._update_phantom_reserved_quantity_for_kit_products()
        log_line_vals = {
            'name': "Export Stock",
            'operation_type': 'export_stock',
        }
        parent_log_line_id = False
        shopify_initial_id = False
        shopify_picking, adjustment = self._verify_shopify_picking()
        # if not shopify_picking:
        shopify_prod_obj = self.env['shopify.product.product']
        error_log_env = self.env['shopify.error.log']
        shopify_log_line_obj = self.env['shopify.log.line']
        product_id = self.check_product_creditibility()
        try:
            shopify_log_id = False
            if taken_quantity > 0:
                negative_qty = taken_quantity * -1
                location_id = self._check_if_child_location(self.location_id)
                location_mapping_ids = self.env['shopify.location.mapping'].search([
                    ('odoo_location_id', '=', location_id.id),
                    ('shopify_config_id.active', '=', True)])
                shopify_location_recs = location_mapping_ids
                for shopify_location_rec in shopify_location_recs:
                    if shopify_location_rec:
                        # and shopify_location_rec.shopify_config_id.sync_inventory_on_reservation:
                        shopify_config_rec = shopify_location_rec.shopify_config_id
                        if shopify_config_rec != shopify_initial_id:
                            shopify_initial_id = shopify_config_rec
                            log_line_vals.update({
                                'shopify_config_id': shopify_config_rec.id,
                            })
                            parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                        # shopify_config_rec.check_connection()
                        shopify_location_id = shopify_location_rec.shopify_location_id
                        error_log_env.create_update_log(
                            shopify_config_id=shopify_config_rec,
                            operation_type='export_stock')
                        if product_id:
                            shopify_product1 = shopify_prod_obj.with_user(
                                self.env.user).search([
                                    ('product_variant_id', '=', product_id.id),
                                    ('shopify_config_id', '=',
                                     shopify_config_rec.id)], limit=1)
                            inventory_item_id = \
                                shopify_product1.shopify_inventory_item_id
                            # shopify_product_cost = product_rec.standard_price
                            if inventory_item_id and \
                                    shopify_product1.update_shopify_inv:
                                name = "%s - %s" % (
                                    shopify_location_rec.odoo_location_id.display_name,
                                    shopify_product1.product_variant_id.display_name)
                                job_descr = _(
                                    "Export Stock to shopify: %s") % (
                                                    name and name.strip())
                                log_line_id = shopify_log_line_obj.create(
                                    {
                                        'name': job_descr,
                                        'shopify_config_id': shopify_config_rec.id,
                                        'id_shopify': f"Location: "
                                                      f"{shopify_location_rec.shopify_location_id or ''} Product: {shopify_product1.shopify_product_id}",
                                        'operation_type': 'export_stock',
                                        'parent_id': parent_log_line_id.id
                                    })
                                qty = self.env['stock.quant']._get_quantity_with_child_locations(
                                    shopify_location_rec.odoo_location_id, shopify_product1.product_variant_id)
                                shopify_config_rec.with_user(
                                    self.env.user).with_company(shopify_config_rec.default_company_id).with_delay(
                                    description=job_descr,
                                    max_retries=5).update_shopify_inventory(
                                    shopify_location_id, inventory_item_id,
                                    int(qty), log_line_id)
                    if parent_log_line_id:
                        parent_log_line_id.update({
                            'state': 'success',
                            'message': 'Operation Successful'
                        })
        except Exception as e:
            if parent_log_line_id:
                parent_log_line_id.update({
                    'state': 'error',
                    'message': traceback.format_exc(),
                })
            # error_message = "Stock update operation have following " \
            #                 "error %s" % e
            # if shopify_log_id:
            #     error_log_env.create_update_log(
            #         shop_error_log_id=shopify_log_id,
            #         shopify_log_line_dict={
            #             'error': [
            #                 {'error_message': error_message}]})
            #
            #     _logger.error(
            #         'Stock update operation have following error: %s', e)
        return taken_quantity


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        res = super(StockRule, self)._get_stock_move_values(
            product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        if values.get('sale_line_id') and values.get('group_id'):
            order_id = values['group_id'].sale_id
            if order_id and order_id.shopify_order_id:
                sale_line_id = self.env['sale.order.line'].sudo().browse(
                    [values.get('sale_line_id')])
                shopify_location_id = sale_line_id.assigned_location_id
                if not shopify_location_id:
                    shopify_location_id = sale_line_id.shopify_location_id
                if shopify_location_id:
                    location_id = self.env['shopify.location.mapping'].search([
                        ('shopify_location_id', '=', shopify_location_id),
                        ('shopify_config_id', '=', order_id.shopify_config_id.id)], limit=1)
                    if location_id:
                        operation_type = (
                                location_id.warehouse_id and
                                location_id.warehouse_id.out_type_id or False)
                        res.update({
                            'location_id': location_id.odoo_location_id.id,
                            'shopify_item_line_id': sale_line_id.shopify_line_id,
                            'shopify_assigned_location_id':
                                sale_line_id.assigned_location_id,
                            'shopify_fulfillment_order_id':
                                sale_line_id.shopify_fulfillment_order_id,
                            'shopify_fulfillment_line_id': sale_line_id.shopify_fulfillment_line_id})
                        if operation_type:
                            res.update({'picking_type_id': operation_type.id})
        return res

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_inventory_move_values(self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False):
        res = super(StockQuant, self)._get_inventory_move_values(qty, location_id, location_dest_id, package_id, package_dest_id)
        if self._context.get('shopify_adjustment'):
            res.update({'shopify_adjustment': self._context.get('shopify_adjustment')})
        return res

    def _get_quantity_with_child_locations(self, location_id, product_id):
        qty = 0
        all_locations = self.env['stock.location'].search(
            [('id', 'child_of', location_id.id)]).ids
        quants = self.with_user(
            self.env.user).search(
            [('location_id', 'in', all_locations),
             ('location_id.usage', '=', 'internal'),
             ('product_id', '=', product_id.id),
             ])
        for quant in quants:
            qty += (quant.quantity - quant.reserved_quantity)
        return qty
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
    is_updated_in_shopify = fields.Boolean(string='Updated In Shopify?',copy=False,readonly=True,default=False)
    shopify_refund_id = fields.Char("Shopify Refund ID", copy=False)

    def _create_backorder(self):
        res = super(StockPicking,self)._create_backorder()
        if self.shopify_config_id:
            res.write({'shopify_config_id': self.shopify_config_id.id})
        return res

    def button_validate(self):
        if self.picking_type_id.code == 'outgoing':
            res = super(StockPicking, self).button_validate()
            if not self._context.get('shopify_picking_validate'):
                shopify_picking_ids = self.filtered(lambda
                                                        r: r.shopify_config_id and not r.is_updated_in_shopify \
                                                           and r.location_dest_id.usage == 'customer' and r.state == 'done')
                if shopify_picking_ids:
                    for picking in shopify_picking_ids:
                        name = self.sale_id.name or ''
                        self.env['sale.order'].shopify_update_order_status(
                            picking.shopify_config_id, picking_ids=picking)
                        shopify_config_id = picking.shopify_config_id
                        if shopify_config_id.is_auto_invoice_paid:
                            if any(self.sale_id.order_line.filtered(
                                    lambda s: s.product_uom_qty ==
                                              s.qty_delivered and
                                              s.product_uom_qty != s.qty_invoiced)) and not any(
                                self.sale_id.invoice_ids.filtered(
                                    lambda i: i.move_type == 'out_invoice' and
                                              i.state == 'posted')):
                                self.sale_id.create_shopify_invoice(
                                    shopify_config_id)
                        # seconds += 2
            return res
        else:
            return super(StockPicking, self).button_validate()

class StockMoveLine(models.Model):

    _inherit = 'stock.move.line'

    shopify_error_log = fields.Text(
        "Shopify Error",
        help="Error occurs while exporting move to the shopify",
        readonly=True)
    shopify_export = fields.Boolean(
        "Shopify Export", readonly=True)

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

    def _verify_shopify_picking(self):
        shopify_picking = adjustment = False
        for move_line in self:
            if (move_line.picking_id.picking_type_id.code in [
                'outgoing', 'internal', 'incoming'] or move_line.reference
                    == 'Product Quantity Updated'):
                # exclude the method call if action done happening while shopify order
                if move_line.reference == 'Product Quantity Updated':
                    adjustment = True
                if not shopify_picking :
                    if not move_line.exists():
                        continue
                    if move_line.picking_id.sale_id:
                        if move_line.picking_id.sale_id.shopify_order_id:
                            shopify_picking = True
        return shopify_picking, adjustment

    def check_product_creditibility(self):
        '''Method added to extended into shopify-roaster extend module'''
        return self.product_id

    def phantom_product_stock_update_for_kit_products(self):
        return

    def _action_done(self):
        """ this method override for update shopify stock
        :return:
        """
        shopify_log_line_obj = self.env['shopify.log.line']
        error_log_env = self.env['shopify.error.log']
        if self.move_id and True in self.move_id.mapped(
                'is_inventory') and True in self.move_id.mapped(
                'shopify_adjustment'):
            return super(StockMoveLine, self)._action_done()

        res = super(StockMoveLine, self)._action_done()
        shopify_picking = self._context.get('shopify_picking_validate')
        adjustment = False
        if not shopify_picking:
            shopify_picking, adjustment = self._verify_shopify_picking()

        # if not shopify_picking:
        shopify_prod_obj = self.env['shopify.product.product']
        shopify_export_val, shopify_log_id = False, False
        seconds = 10

        log_line_vals = {
            'name': "Export Stock",
            'operation_type': 'export_stock',
        }
        parent_log_line_id = False
        shopify_initial_id = False
        self.phantom_product_stock_update_for_kit_products()
        for move in self:
            # Need to check whether move exists or not as when receiving
            # partial quantities system will remove moves
            # move_exists = self.search([('id', '=', move.id)])
            # if not move_exists:
            #     continue
            if not move.exists():
                continue
            try:
                product_rec = move.check_product_creditibility()
                if not product_rec:
                    continue
                product_id = product_rec
                product_count = \
                    shopify_prod_obj.with_user(
                        self.env.user).search_count([
                        ('product_variant_id', '=', product_id.id),
                        ('shopify_product_id', 'not in', ('', False))
                    ])
                qty = move.quantity
                if product_count > 0 and qty > 0:
                    negative_qty = qty * -1
                    # location_id = move.location_id
                    location_id = self.env['stock.move']._check_if_child_location(
                        move.location_id)
                    # location_dest_id = move.location_dest_id
                    location_dest_id = self.env['stock.move']._check_if_child_location(
                        move.location_dest_id)
                    self._check_location_config(location_id,
                                                location_dest_id)
                    location_mapping_ids = self.env[
                        'shopify.location.mapping'].search([
                        ('odoo_location_id', '=', location_id.id),
                        ('shopify_config_id.active', '=', True)
                    ])
                    shopify_location_recs = location_mapping_ids
                    for shopify_location_rec in shopify_location_recs:
                        shopify_config_rec = shopify_location_rec.shopify_config_id
                        # if shopify_picking and shopify_config_rec and move.picking_id.shopify_config_id and not move.move_id.origin_returned_move_id and shopify_config_rec == move.picking_id.shopify_config_id:
                        #     continue
                        # shopify_config_rec.check_connection()
                        shopify_location_id = shopify_location_rec.shopify_location_id
                        if not shopify_log_id:
                            shopify_log_id = error_log_env.create_update_log(
                                shopify_config_id=shopify_config_rec,
                                operation_type='export_stock')
                        shopify_product1 = shopify_prod_obj.with_user(
                            self.env.user).search([
                            ('product_variant_id', '=', product_id.id),
                            ('shopify_config_id', '=',
                             shopify_config_rec.id)], limit=1)
                        inventory_item_id = \
                            shopify_product1.shopify_inventory_item_id
                        # shopify_product_cost = product_rec.standard_price
                        if inventory_item_id and \
                                shopify_product1.update_shopify_inv:
                            name = "%s - %s" % (
                                shopify_location_rec.odoo_location_id.display_name,
                                shopify_product1.product_variant_id.display_name)
                            job_descr = _(
                                "Export Stock to shopify: %s") % (
                                                name and name.strip())
                            if shopify_initial_id != shopify_config_rec:
                                shopify_initial_id = shopify_config_rec
                                log_line_vals.update({
                                    'shopify_config_id': shopify_config_rec.id,
                                })
                                parent_log_line_id = shopify_log_line_obj.create(log_line_vals)

                            log_line_id = (
                                shopify_log_line_obj.create(
                                    {
                                        'name': job_descr,
                                        'shopify_config_id': shopify_config_rec.id,
                                        'id_shopify': f"Location: "
                                                      f"{shopify_location_rec.shopify_location_id or ''} Product: {shopify_product1.shopify_product_id}",
                                        'operation_type': 'export_stock',
                                        'parent_id': parent_log_line_id.id
                                    }))

                            qty = self.env['stock.quant']._get_quantity_with_child_locations(
                                location_id, shopify_product1.product_variant_id)
                            eta = datetime.now() + timedelta(
                                seconds=seconds)
                            shopify_config_rec.with_user(
                                self.env.user).with_company(shopify_config_rec.default_company_id).with_delay(
                                description=job_descr,
                                max_retries=5,
                                eta=eta).update_shopify_inventory(
                                shopify_location_id,
                                inventory_item_id,
                                int(qty), log_line_id)
                            shopify_export_val = True
                            seconds +=1
                        if parent_log_line_id:
                            parent_log_line_id.update({
                                'state': 'success',
                                'message': 'Operation Successful'
                            })
                    # Destination location inventory update
                    location_dest_mapping_ids = self.env[
                        'shopify.location.mapping'].search([
                        ('odoo_location_id', '=',
                         location_dest_id.id),
                        ('shopify_config_id.active', '=', True)])
                    shopify_location_recs = location_dest_mapping_ids
                    for shopify_location_rec in shopify_location_recs:
                        shopify_config_rec = shopify_location_rec.shopify_config_id
                        # if shopify_picking and shopify_config_rec and move.picking_id.shopify_config_id and not move.move_id.origin_returned_move_id and shopify_config_rec == move.picking_id.shopify_config_id:
                        #     continue
                        # shopify_config_rec.check_connection()
                        shopify_location_id = shopify_location_rec.shopify_location_id
                        if not shopify_log_id:
                            shopify_log_id = error_log_env.create_update_log(
                                shopify_config_id=shopify_config_rec,
                                operation_type='export_stock')
                        shopify_product1 = shopify_prod_obj.with_user(
                            self.env.user).search([
                            ('product_variant_id', '=', product_id.id),
                            ('shopify_config_id', '=',
                             shopify_config_rec.id)], limit=1)
                        inventory_item_id = \
                            shopify_product1.shopify_inventory_item_id
                        # shopify_product_cost = product_rec.standard_price
                        if inventory_item_id and \
                                shopify_product1.update_shopify_inv:
                            name = "%s - %s" % (
                                shopify_location_rec.odoo_location_id.display_name,
                                shopify_product1.product_variant_id.display_name)
                            job_descr = _(
                                "Export Stock to shopify: %s") % (
                                                name and name.strip())

                            if (shopify_initial_id != shopify_config_rec) or (not parent_log_line_id) or (
                                    parent_log_line_id and parent_log_line_id.shopify_config_id.id != shopify_config_rec.id):
                                shopify_initial_id = shopify_config_rec
                                log_line_vals.update({
                                    'shopify_config_id': shopify_config_rec.id,
                                })
                                parent_log_line_id = shopify_log_line_obj.create(log_line_vals)
                            log_line_id = (
                                shopify_log_line_obj.create(
                                    {
                                        'name': job_descr,
                                        'shopify_config_id': shopify_config_rec.id,
                                        'id_shopify': f"Location: "
                                                      f"{shopify_location_rec.shopify_location_id or ''} Product: {shopify_product1.shopify_product_id}",
                                        'operation_type': 'export_stock',
                                        'parent_id': parent_log_line_id.id
                                    }))
                            qty = self.env['stock.quant']._get_quantity_with_child_locations(
                                location_dest_id, shopify_product1.product_variant_id)
                            eta = datetime.now() + timedelta(
                                seconds=seconds)
                            shopify_config_rec.with_user(
                                self.env.user).with_company(shopify_config_rec.default_company_id).with_delay(
                                description=job_descr,
                                max_retries=5,
                                eta=eta).update_shopify_inventory(
                                shopify_location_id,
                                inventory_item_id,
                                int(qty), log_line_id)
                            shopify_export_val = True
                            seconds += 2
                        if parent_log_line_id:
                            parent_log_line_id.update({
                                'state': 'success',
                                'message': 'Operation Successful'
                            })
                if shopify_export_val:
                    move.shopify_export = shopify_export_val
                # error_message = "Stock updated queue created."
                # _logger.info(error_message)
            except Exception as e:
                error_message = "Stock update operation have following " \
                                "error %s" % e
                if parent_log_line_id:
                    parent_log_line_id.update({
                        'state': 'error',
                        'message': error_message,
                    })
                # if shopify_log_id:
                #     error_log_env.create_update_log(
                #         shop_error_log_id=shopify_log_id,
                #         shopify_log_line_dict={
                #             'error': [
                #                 {'error_message': error_message}]})
                #
                #     _logger.error(
                #         'Stock update operation have following error: %s',
                #         e)
                # move.shopify_error_log = str(e)
        return res

class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.valuation.layer'

    @api.model
    def create(self, vals):
        """
        :param vals: update date based move done date
        :return: recordset
        """
        rec = super(StockValuationLayer, self).create(vals)
        if rec.stock_move_id:
            self.env.cr.execute(
                """UPDATE stock_valuation_layer SET create_date = %(date)s 
                    WHERE id = %(rec_id)s""",
                {'date': rec.stock_move_id.date,
                 'rec_id': rec.id})
        return rec
