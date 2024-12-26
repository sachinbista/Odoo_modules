# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import float_compare, float_round


class InterCompanyStockTransferLine(models.Model):
    _name = 'inter.company.stock.transfer.line'
    _description = 'Stock Transfer Lines'
    _order = 'location_id asc'

    name = fields.Char('Description', index=True)
    stock_transfer_id = fields.Many2one('inter.company.stock.transfer')
    product_id = fields.Many2one(
        'product.product', domain="[('type', '=', 'product')]")
    product_uom = fields.Many2one('uom.uom')
    product_uom_qty = fields.Float('Initial Demand')
    lot_id = fields.Many2one('stock.lot', 'Lot')
    location_id = fields.Many2one(
        'stock.location', string='Quant Location')
    package_id = fields.Many2one('product.packaging', 'Packaging Type')
    is_single_ship = fields.Boolean(string="Single Ship", default=False)
    package_quant_id = fields.Many2one('stock.quant.package', 'Package')

    # @api.model
    # def create(self, vals):
    #     res = super(InterCompanyStockTransferLine, self).create(vals)
    #     if res and res.stock_transfer_id.state in ('in_progress', 'done'):
    #         res.stock_transfer_id.update_inventory_allocation()
    #     return res

    # def write(self, vals):
    #     res = super(InterCompanyStockTransferLine, self).write(vals)
    #     for rec in self:
    #         if vals.get('product_uom_qty', False) and \
    #                 rec.stock_transfer_id.state in ('in_progress', 'done'):
    #             ctx = dict(self.env.context) or {}
    #             ctx.update({'tl_quantity_change': True})
    #             rec.stock_transfer_id.update_inventory_allocation()
    #     return res

    def _check_package(self):
        default_uom = self.product_id.uom_id
        pack = self.package_id
        qty = self.product_uom_qty
        q = default_uom._compute_quantity(pack.qty, self.product_uom)
        if (qty and q and float_compare(
                qty / q, float_round(
                    qty / q, precision_rounding=1.0
                ), precision_rounding=0.001) != 0):
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': (_(
                        "Product %s is transfer in the \
                        multiple of package of %.2f %s,\
                        you should transfer in quantity of \
                        product in a multiple of package." % (
                            self.product_id.name, pack.qty, default_uom.name)
                    ))
                },
            }
        return {}

    @api.onchange('package_id')
    def _onchange_product_packaging_inter(self):
        if self.package_id:
            return self._check_package()

    @api.onchange('product_id')
    def onchange_product_id(self):
        product = self.product_id.with_context(lang=self.env.user.lang)
        self.product_uom = product.uom_id.id
        self.name = product.partner_ref or ''
        return {
            'domain': {
                'product_uom': [
                    ('category_id', '=', product.uom_id.category_id.id)
                ]
            }
        }

    def _prepare_procurement_values(self, company_id, warehouse_id, group_id):
        self.ensure_one()
        values = {}
        date_planned = self.stock_transfer_id and\
            self.stock_transfer_id.scheduled_date
        values.update({
            'group_id': group_id,
            'date_planned': date_planned,
            'warehouse_id': warehouse_id,
            'partner_id': self.stock_transfer_id.dest_company_id.partner_id.id,
            'company_id': company_id,
        })
        if warehouse_id and warehouse_id.outgoing_route_id:
            values.update(({
                'route_ids': warehouse_id.outgoing_route_id,
            }))

        if self.lot_id:
            values.update({'serial_number_ids': [(6, 0, self.lot_id.ids)]})
        return values

    def _prepare_stock_moves(
            self, picking, picking_type_id, location_id, dest_location_id,
            dest_company_id):
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res

        if picking_type_id.warehouse_id and \
                picking_type_id.warehouse_id.incoming_route_id:
            route_ids = [
                (6, 0, [picking_type_id.warehouse_id.incoming_route_id.id])]
        elif picking_type_id.warehouse_id:
            route_ids = [(6, 0, picking_type_id.warehouse_id.route_ids.ids)]
        else:
            route_ids = []
        template = {
            'name': (self.name or '')[:2000],
            'product_id': self.product_id.id,
            'state': 'draft',
            'product_uom': self.product_uom.id,
            'product_uom_qty': self.product_uom_qty,
            'date': self.stock_transfer_id.exp_arrival_date if self.stock_transfer_id.exp_arrival_date else self.stock_transfer_id.scheduled_date,
            'location_id': location_id,
            'location_dest_id': dest_location_id,
            'picking_id': picking.id,
            'company_id': dest_company_id.id,
            'picking_type_id': picking_type_id.id,
            'group_id': self.stock_transfer_id.group_id.id,
            'origin': self.stock_transfer_id.name,
            'route_ids': route_ids,
            'warehouse_id': picking_type_id.warehouse_id.id,
            'procure_method': 'make_to_stock',
        }
        product_qty = self.product_uom_qty
        procurement_uom = self.product_uom
        quant_uom = self.product_id.uom_id
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if procurement_uom.id != quant_uom.id and get_param(
                'stock.propagate_uom') != '1':
            product_qty, procurement_uom = self.product_uom._adjust_uom_quantities(product_qty, quant_uom)
            template['product_uom'] = quant_uom.id
            template['product_uom_qty'] = product_qty
        res.append(template)
        return res

    def _create_stock_moves(
            self, picking, picking_type_id, location_id, dest_location_id,
            dest_company_id):
        ctx = dict(self._context)
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        with self.env.norecompute():
            list_vals = []
            for line in self:
                for vals in line.with_context(ctx)._prepare_stock_moves(
                        picking, picking_type_id, location_id,
                        dest_location_id, dest_company_id):
                    list_vals.append(vals)
            product_filtered_dict = self.product_filtered_dict(list_vals)
            done += moves.with_context(ctx).create(product_filtered_dict)
        return done

    def product_filtered_dict(self, values):
        """
            Product wise filtered dict
        """
        list_product = []
        for pd in values:
            if pd.get('product_id') and pd['product_id'] in\
                [pro['product_id'] for pro in list_product if pro.get(
                    'product_id')]:
                [pro.update({'product_uom_qty': sum([float(pro.get(
                    'product_uom_qty')), float(pd.get('product_uom_qty'))])
                }) for pro in list_product if pro.get('product_id') and
                    pd.get('product_id') and pro['product_id'] == pd.get(
                        'product_id')]
            else:
                list_product.append(pd)
        return list_product

    def _create_stock_move_lines(self, picking):
        ctx = dict(self._context)
        done_move = self.env['stock.move'].browse()
        with self.env.norecompute():
            lot_ids = {}
            package_ids = {}
            for line in self.filtered(lambda l: l.lot_id):
                if lot_ids.get(line.product_id.id):
                    lot_ids[line.product_id.id].append(line.lot_id.id)
                else:
                    lot_ids.update({line.product_id.id: [line.lot_id.id]})

            if picking and not picking.prev_picking_id:
                for move_id in picking.move_ids:
                    m_lot_ids = lot_ids.get(move_id.product_id.id or [])
                    m_package_ids = package_ids.get(move_id.product_id.id or [])
                    if m_lot_ids:
                        ctx.update({
                            'lot_numbers': m_lot_ids,
                            'is_intercompany_resupply': True})

                    done_move += move_id.with_context(ctx)._action_confirm()
        return done_move

    def create_inter_warehouse_stock_move_lines(self, picking):
        if picking and not picking.prev_picking_id:
            for line in self:
                move_id = picking.move_ids.filtered(lambda m: m.product_id.id == line.product_id.id)
                move_id._action_inter_warehouse_transfer_assign(line)
                for move_line in move_id.move_line_ids:
                    move_line.result_package_id = move_line.package_id and move_line.package_id.id or False
