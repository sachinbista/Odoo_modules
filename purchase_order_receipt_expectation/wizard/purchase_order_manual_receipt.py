# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderManualReceipt(models.TransientModel):
    _name = 'purchase.order.manual.receipt.wizard'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    scheduled_date = fields.Datetime(string="Scheduled Date", default=fields.Datetime.now)
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="purchase_order_id.company_id")
    picking_type_id = fields.Many2one('stock.picking.type', string='Deliver To', domain="[('code', '=', 'incoming'), '|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]")
    auto_confirm_picking = fields.Boolean(string="Auto Confirm Picking", default=True)
    checks_result = fields.Selection([('success', 'Success'), ('failure', 'Failure')], default='success')
    checks_result_msg = fields.Text()
    line_ids = fields.One2many('purchase.order.manual.receipt.line', 'manual_receipt_id')


    def default_get(self, fields_list):
        res = super(PurchaseOrderManualReceipt, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        purchase_order_id = self.env['purchase.order'].browse(active_id)
        if purchase_order_id:
            res.update({
                'purchase_order_id': purchase_order_id.id,
                'picking_type_id': purchase_order_id.picking_type_id.id,
            })
        if purchase_order_id.order_line:
            lines = []
            for line in purchase_order_id.order_line:
                qty = line.product_uom_qty - line.manually_received_qty_uom
                if qty > 0:
                    lines.append((0, 0, {'product_id': line.product_id.id,
                                          'product_uom_qty': qty,
                                          'unit_price': line.price_unit,
                                          'purchase_line_id': line.id,
                                          'uom_id': line.product_uom,
                                          }))
            res.update({'line_ids': lines})
        return res


    def _prepare_picking(self):
        order = self.purchase_order_id
        if not order.group_id:
            order.group_id = order.group_id.create({
                'name': order.name,
                'partner_id': order.partner_id.id
            })
        if not order.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", order.partner_id.name))
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': order.partner_id.id,
            'user_id': False,
            'date': self.scheduled_date,
            'origin': order.name,
            'location_dest_id': order._get_destination_location(),
            'location_id': order.partner_id.property_stock_supplier.id,
            'company_id': order.company_id.id,
        }

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        order = self.purchase_order_id
        if any(product.type in ['product', 'consu'] for product in self.line_ids.product_id):
            order = order.with_company(order.company_id)
            picking = self.env['stock.picking'].search(
                [('group_id.name', '=', self.purchase_order_id.name), ('container_id', '=', self.container_id),
                 ('state', 'not in', ('done', 'cancel'))])
            if not picking:
                res = self._prepare_picking()
                picking = StockPicking.with_user(SUPERUSER_ID).create(res)
            moves = self.line_ids._create_stock_moves(picking)
            moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
            seq = 0
            for move in sorted(moves, key=lambda move: move.date):
                seq += 5
                move.sequence = seq
            moves._action_assign()
            # Get following pickings (created by push rules) to confirm them as well.
            forward_pickings = self.env['stock.picking']._get_impacted_pickings(moves)
            forward_pickings.update({
                    'receive_by_container': self.container_id
                    })
            (picking | forward_pickings).action_confirm()
            picking.message_post_with_view('mail.message_origin_link',
                values={'self': picking, 'origin': order},
                subtype_id=self.env.ref('mail.mt_note').id)

            #code by aaftab po state locked
            self.purchase_order_id.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
            return picking
        else:
            return False

    def _get_action_view_picking(self, pickings):
        """ This function returns an action that display existing picking orders of given purchase order ids. When only one found, show the picking immediately.
        """
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_origin': self.name, 'default_picking_type_id': self.picking_type_id.id}
        # choose the view_mode accordingly
        if not pickings or len(pickings) > 1:
            result['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = pickings.id
        return result

    def button_check(self):
        print("check")
        return

    def button_confirm(self):
        self._create_picking()
        return