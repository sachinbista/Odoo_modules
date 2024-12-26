# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    target_model = fields.Selection(selection_add=[
        ('purchase', "Purchase Orders")
    ], ondelete={'purchase': 'set default'}, default='purchase')
    po_ids = fields.Many2many(
        'purchase.order', string='Purchase Orders',
        copy=False, states={'done': [('readonly', True)]}, groups='stock.group_stock_manager')
    state = fields.Selection(selection_add=[("confirmed", "Confirmed"), ("done",)]
                             , ondelete={"confirmed": "set default"})
    is_all_received = fields.Boolean(string='All Transfers Received', compute='_compute_is_all_received',default=False, copy=False, store=True)
    container_id = fields.Char(string="Container", copy=False)

    
    @api.onchange('target_model')
    def _onchange_target_model(self):
        super()._onchange_target_model()
        if self.target_model != 'purchase':
            self.po_ids = False

    @api.depends('po_ids')
    def _compute_is_all_received(self):
        self.is_all_received = False
        if self.po_ids and self.po_ids.mapped('picking_ids'):
            all_pickings = self.po_ids.mapped('picking_ids').filtered(
                lambda picking: picking.state != 'cancel' and picking.picking_type_id.code == 'incoming')
            if all(p.state == 'done' for p in all_pickings) and self.target_model == 'purchase':
                self.is_all_received = True
            else:
                self.is_all_received = False

    def _check_can_validate(self):
        if any(cost.state not in ['draft','confirmed'] for cost in self):
            raise UserError(_('Only draft & confirmed landed costs can be validated'))
        for cost in self:
            if not cost._get_targeted_move_ids():
                target_model_descriptions = dict(self._fields['target_model']._description_selection(self.env))
                raise UserError(_('Please define %s on which those additional costs should apply.', target_model_descriptions[cost.target_model]))

    def button_validate(self):
        if self.po_ids:
            picking_ids = self.po_ids.mapped('picking_ids').filtered(lambda s: s.picking_type_id.code == 'incoming')
            picking_po = self.picking_ids.mapped('move_ids').mapped('purchase_line_id').mapped('order_id')
            if 'is_manually' in self._context:
                self._compute_is_all_received()
            if self.is_all_received:
                self.update({
                    'picking_ids': self.po_ids.mapped('picking_ids').filtered(lambda s: s.picking_type_id.code=='incoming' and s.state=='done')
                    })
            elif  len(picking_po) != len(self.po_ids):
                return True

        return super(StockLandedCost, self).button_validate()

    def button_confirm(self):
        # Set the state to "confirmed"
        if self.po_ids:
            fully_received_picking = self.po_ids.filtered(lambda s: s.receipt_status == 'full').mapped('picking_ids').filtered(lambda s: s.picking_type_id.code =='incoming')
            self.update({
                'picking_ids': fully_received_picking.ids if fully_received_picking else False,
                'state': 'confirmed'
                })
        else:
            self.update({
                'state': 'confirmed'
                })
        return True


    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            product_ids = self.env['product.product']
            rounding = cost.currency_id.rounding
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    if cost_line.split_method =='by_weight' and not val_line_values.get('weight', 0.0):
                        product_id = self.env['product.product'].browse(val_line_values.get('product_id'))
                        if product_id not in product_ids:
                            product_ids |= product_id
                    elif cost_line.split_method == 'by_volume' and not val_line_values.get('volume', 0.0):
                        product_id = self.env['product.product'].browse(val_line_values.get('product_id'))
                        if product_id not in product_ids:
                            product_ids |= product_id
            if product_ids:
                warn_msg = _('Please Configure Volume/Weight For Product is:%s',',\n \n'.join(x.display_name for x in product_ids))
                raise UserError(warn_msg)
            else:
                return super(StockLandedCost, self).compute_landed_cost()

    def update_purchase_order(self):
        if self.container_id:
            self.set_purchase_order()

    @api.onchange('container_id')
    def set_purchase_order(self):
        if self.container_id:
            move_ids= self.env['stock.move'].search([('picking_id.container_id','=', self.container_id),('picking_id.state','!=', 'cancel')])
            self.po_ids = [x.id for x in move_ids.mapped('purchase_line_id.order_id')]
        else:
            self.po_ids = False

    @api.constrains('container_id')
    def check_container_existence(self):
        """ Raises: UserError if duplicates container are found. """
        for record in self:
            # Check if a container_id is set
            if record.container_id:
                # Search for duplicates with the same container_id
                duplicates = record.search([('container_id', '=', record.container_id),
                                            ('state', 'in', ('draft','confirmed')),
                                            ('id', '!=', record.id),  # Exclude the current record
                                            ],limit=1)
                # Raise UserError if duplicates are found
                if duplicates:
                    raise UserError(_("This '%s' container is already exists. that is in '%s' state \n Go to this landed cost:'%s' and use Refresh button option!!", record.container_id, duplicates.state.capitalize(),  duplicates.name))

    def unlink_purchase_order(self):
        if self.container_id and self.po_ids and len(self.po_ids) == 1:
            self.state = 'cancel'
        if self.container_id and self.po_ids and len(self.po_ids) > 1:
            line_vals=[]
            for po_id in self.po_ids:
                line_vals.append((0, 0, {'purchase_order_id': po_id.id}))

            view = self.env.ref('bista_landed_costs.landed_cost_unlink_wizard')
            return {
                'name': _('To Unlink Landed Cost'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'landedcost.unlink',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'context': dict(self.env.context, default_landedcost_id=self.id, default_landedcost_unlink_line=line_vals),
                }



            
