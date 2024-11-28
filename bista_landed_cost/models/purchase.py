from odoo import models, api,fields,_


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    landed_cost_count = fields.Integer('Landed Cost Count',compute="_compute_landed_cost_count")
    landed_cost_ids = fields.Many2many('stock.landed.cost')
    transit_move_ids = fields.One2many('account.move', 'transit_id', string='Transit Moves')
    is_transit = fields.Boolean('Is Transit', compute='_compute_is_transit', store=True)

    @api.depends('company_id.is_transit')
    def _compute_is_transit(self):
        for rec in self:
            if rec.company_id.is_transit:
                rec.is_transit = True
            else:
                rec.is_transit = False

    def action_view_transit_move(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        action['domain'] = [('id', 'in', self.transit_move_ids.ids)]
        return action

    def button_transit(self):
        return {
            'name': _('Create In-Transit Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'transit.wizard',
            'view_id': self.env.ref('bista_landed_cost.transit_wizard_view_form').id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_id': self.id,
                        'default_transit_line_ids': [(0, 0, {
                            'product_id': line.product_id.id,
                            'price': line.price_subtotal,
                            'purchase_line_id': line.id,
                            'is_transit': line.is_transit}) for line in self.order_line]
                        }
        }



    @api.depends('picking_ids')
    def _compute_landed_cost_count(self):
        for rec in self:
            if  rec.picking_ids:
                landed_cost_ids = self.env['stock.landed.cost'].search([('picking_ids','=',rec.picking_ids.ids)])

                rec.landed_cost_count = len(landed_cost_ids)
                rec.landed_cost_ids = landed_cost_ids.ids
            else:
                rec.landed_cost_count = 0

    def action_view_landed_costs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        domain = [('id', 'in', self.landed_cost_ids.ids)]
        context = dict(self.env.context, default_vendor_bill_id=self.id)
        views = [(self.env.ref('stock_landed_costs.view_stock_landed_cost_tree2').id, 'tree'), (False, 'form'), (False, 'kanban')]
        return dict(action, domain=domain, context=context, views=views)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_transit = fields.Boolean(string="Transit Created",copy=False)
