# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


class Location(models.Model):
    _inherit = 'stock.location'

    show_as_virtual_location = fields.Boolean(
        string="Show Location in Picking")
    is_intercompany = fields.Boolean(
        string="Resupply Operation",
        default=False,
        readonly=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        compute='_compute_warehouse_id',
        store=True)

    @api.depends('name', 'location_id.complete_name', 'usage')
    def _compute_complete_name(self):
        physical_location = self.env.ref('stock.stock_location_locations')
        virtual_location = self.env.ref(
            'stock.stock_location_locations_virtual')
        for location in self:
            if location.location_id and location.usage != 'view':
                complete_name = '%s/%s' % (
                    location.location_id.complete_name, location.name)
                if physical_location.name in complete_name:
                    complete_name = complete_name.split(
                        physical_location.name + "/", 1)[1]
                elif virtual_location.name in complete_name:
                    complete_name = complete_name.split(
                        virtual_location.name + "/", 1)[1]
                else:
                    complete_name = complete_name
                location.complete_name = complete_name
            else:
                location.complete_name = location.name

    def should_bypass_reservation(self):
        """
            Overwritten method based on context
            condition to remove 'customer'
            related condition checking when
            returning shipment in case of
            inter-company and returning out shipment.
        """
        self.ensure_one()
        if self._context.get('intercomp_call_to_change_bypass_method', False):
            return self.usage in (
                'supplier', 'inventory',
                'production') or self.scrap_location
        return super(Location, self).should_bypass_reservation()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('ctx_picking_type') and self._context.get(
                'ctx_location'):
            domain = args or []
            picking_type_id = self.env['stock.picking.type'].search([
                ('id', '=', self._context['ctx_picking_type'])])
            if picking_type_id and picking_type_id.code in [
                    'incoming', 'internal']:
                flag = True
                if self._context.get('ctx_picking_id') and self._context.get(
                        'ctx_line_product'):
                    move_id = self.env['stock.move'].search([
                        ('product_id', '=', self._context['ctx_line_product']),
                        ('picking_id', '=', self._context['ctx_picking_id'])
                    ], limit=1)

                    if picking_type_id.code == 'incoming' and\
                            move_id.move_dest_ids:
                        flag = False
                    if picking_type_id.code == 'internal' and \
                            not move_id.move_orig_ids:
                        flag = False
                if flag:
                    location_id = self.search(
                        [('id', '=', self._context['ctx_location'])])
                    if location_id and location_id.location_id:
                        location_ids = self.search([
                            ('id', 'child_of', location_id.location_id.ids),
                            ('show_as_virtual_location', '=', True)])
                        domain = expression.OR(
                            [domain, [('id', 'in', location_ids.ids)]])
                        return self.search(domain, limit=limit).name_get()
        if self._context.get('warehouse_id', False) and\
                not self._context.get('lot_id', False):
            domain = args or []
            if self._context.get('warehouse_id', False):
                domain = expression.AND([
                    args or [],
                    ['|', ('barcode', operator, name),
                     ('complete_name', operator, name),
                     ('usage', '=', 'internal'),
                     ('company_id', '=', self._context.get('company_id'))]
                ])
            return self.search(domain, limit=limit).name_get()
        elif self._context.get('warehouse_id', False) and self._context.get(
                'lot_id', False):
            domain = args or []
            all_locations = []
            if self._context.get('warehouse_id', False) and self._context.get(
                    'lot_id', False):
                all_quants = self.env['stock.quant'].search([
                    ('lot_id', '=', self._context.get('lot_id')),
                    ('company_id', '=', self._context.get('company_id'))
                ])
                for quant in all_quants:
                    if quant.location_id and \
                            quant.location_id.id not in all_locations:
                        all_locations.append(quant.location_id.id)
                domain = expression.AND([
                    args or [],
                    ['|', ('barcode', operator, name),
                     ('complete_name', operator, name),
                     ('id', 'in', all_locations)]
                ])
            return self.search(domain, limit=limit).name_get()
        elif self._context.get('warehouse_id', False):
            domain = args or []
            if self._context.get('warehouse_id', False):
                domain = expression.AND([
                    args or [],
                    ['|', ('barcode', operator, name),
                     ('complete_name', operator, name),
                     ('usage', '=', 'internal'),
                     ('company_id', '=', self._context.get('company_id'))]
                ])
            return self.search(domain, limit=limit).name_get()
        return super(Location, self).name_search(name, args, operator, limit)
