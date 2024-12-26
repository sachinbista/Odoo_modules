from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from itertools import groupby
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import calendar
from datetime import timedelta, date


class TransferPackage(models.TransientModel):
    _name = 'transfer.package'
    _description = 'Internal Transfer from Stock Quant.'

    dest_location_id = fields.Many2one('stock.location', string="Destination Location", domain=lambda self: self._compute_dest_location_id_domain())
    result_package_id = fields.Many2one('stock.quant.package', 'Destination Package', domain=lambda self: self._compute_package_domain())
    line_ids = fields.One2many('transfer.package.line', 'transfer_package_id', string="Transfer Package Lines")
    show_success_message = fields.Boolean('Show Success Message', default=False, copy=False, readonly=False, store=True)
    success_message = fields.Text(string="Success Message", readonly=True)

    @api.depends('line_ids')
    def _compute_dest_location_id_domain(self):
        domain = []
        stock_quant_obj = self.env['stock.quant']
        active_ids = self._context.get('active_ids')
        active_quants = stock_quant_obj.browse(active_ids)
        warehouse_ids = set(line.location_id.warehouse_id.id for line in active_quants)
        domain.append(('warehouse_id', 'in', list(warehouse_ids)))
        domain.append(('usage', '=', 'internal'))
        return domain

    @api.depends('line_ids')
    def _compute_package_domain(self):
        domain = []
        stock_quant_obj = self.env['stock.quant']
        active_ids = self._context.get('active_ids')
        active_quants = stock_quant_obj.browse(active_ids)
        package_ids = set(quant.package_id.id for quant in active_quants)
        if package_ids:
            domain.append(('id', 'in', list(package_ids)))
        return domain


    @api.model
    def default_get(self, fields):
        res = super(TransferPackage, self).default_get(fields)
        stock_quant_obj = self.env['stock.quant']

        context_type = self.env.context.get('type')
        if context_type in ('transfer_package', 'merge_package'):
            active_ids = self._context.get('active_ids')
            if not active_ids:
                raise UserError("Please select any record!")
            if context_type == 'merge_package' and not len(active_ids) > 1:
                raise UserError(_("Please select atleast 2 transfers to merge!"))

            active_quants = stock_quant_obj.browse(active_ids)
            # warning_quants = active_quants.filtered(lambda quant: not quant.package_id)
            reserved_quants = active_quants.filtered(lambda quant: quant.reserved_quantity > 0)

            # if warning_quants:
            #     error_message = "The following selected records do not have a package. Please select records with a package:\n"
            #     error_message += "\n".join(
            #         [f"- Location: {quant.location_id.complete_name}, Product: {quant.product_id.name}" for quant in
            #          warning_quants])
            #     raise UserError(error_message)

            if reserved_quants:
                error_message = "Before transfer the package please unreserve the following Stock Quant:\n"
                error_message += "\n".join([
                                               f"- Location: {quant.location_id.complete_name}, Product: {quant.product_id.name}, Package: {quant.package_id.name if quant.package_id else 'N/A'}"
                                               for quant in reserved_quants])
                raise UserError(error_message)

            # package_ids = active_quants.mapped('package_id')
            # for package in package_ids:
            #     package_quants = self.env['stock.quant'].search([
            #         ('package_id', '=', package.id),
            #         ('location_id.usage', '=', 'internal')])
            #     if len(package_quants) > 1:
            #         raise UserError(F"Package {package.name} contains multiple products.")

            lines = [(0, 0, {
                'quant_id': quant.id,
                'product_id': quant.product_id.id,
                'source_location_id': quant.location_id.id,
                'warehouse_id': quant.location_id.warehouse_id.id,
                'qty_available': quant.quantity,
                'qty_transfer': quant.quantity,
                'company_id': quant.company_id.id,
                'package_id': quant.package_id.id,
                'result_package_id': quant.package_id.id
            }) for quant in active_quants]

            res['line_ids'] = lines

        return res


    def action_next_step(self):
        if not self.line_ids:
            raise UserError(_("Please select some lines for transfer!"))

        # Determine the source location IDs from line_ids
        source_location_ids = self.line_ids.mapped('source_location_id')

        # Fetch the parent location of the first source location ID
        location_id = False
        if source_location_ids:
            source_location = source_location_ids[0]
            location_id = source_location.location_id if source_location.location_id else source_location
        if not self.env.context.get('type') == 'transfer_package' and self.dest_location_id:
            dest_location_id =self.dest_location_id
        else:
            dest_location_id = location_id

        # Create a new picking with the parent location as the location_id
        picking_vals = {
            'picking_type_id': dest_location_id.warehouse_id.int_type_id.id,
            'date': fields.Datetime.now(),
            'origin': 'Internal Transfer',
            'location_id': location_id.id,
            'location_dest_id': dest_location_id.id,
            'company_id': self.env.user.company_id.id,
        }
        picking_id = self.env['stock.picking'].sudo().create(picking_vals)

        if not self.env.context.get('type') == 'transfer_package':
            picking_ids = self.create_mergepackage_stock_move(picking_id, self.line_ids)
        else:
            picking_ids = self.create_transfer_package_stock_move(picking_id, self.line_ids)



        if picking_id:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': picking_id.id,
                'target': 'current',
            }
        else:
            return {'type': 'ir.actions.act_window_close'}

    def _prepare_stock_move_vals(self,picking_id,line):
        self.ensure_one()
        return {
            'name': (picking_id.name or '')[:2000],
            'product_id': line.product_id.id,
            'product_uom_qty': line.qty_transfer,
            'product_uom': line.product_id.uom_id.id,
            'location_id': line.source_location_id.id,
            'location_dest_id':line.destination_location_id.id,
            'picking_id': picking_id.id,
        }

    def create_transfer_package_stock_move(self, picking_id, line_ids):
        move_obj = self.env['stock.move']
        for line in line_ids:
            move_id = self.env['stock.move'].create(self._prepare_stock_move_vals(picking_id,line))
            move_id._action_quick_transfer_assign(line)
            # move_vals = {
            #     'name': (picking_id.name or '')[:2000],
            #     'product_id': line.product_id.id,
            #     'product_uom_qty': line.qty_transfer,
            #     'quantity_done': line.qty_transfer,
            #     'product_uom': line.product_id.uom_id.id,
            #     'picking_id': picking_id.id,
            #     'location_id': line.source_location_id.id,
            #     'location_dest_id': line.destination_location_id.id,
            # }
            # move_id= move_obj.create(move_vals)
            # move_objs = picking_id.move_ids.filtered(lambda m: m.product_id == line.product_id)
            # move_objs._action_assign()
            for move in move_id:
                move_line = move.move_line_ids.filtered(lambda ml: ml.product_id.id == move.product_id.id)
                move_line.write({
                    'result_package_id': line.result_package_id.id if line.result_package_id else '',
                    'qty_done': line.qty_transfer,
                })
        picking_id.button_validate()

        return picking_id

    def create_mergepackage_stock_move(self, picking_id, line_ids):
        move_obj = self.env['stock.move']
        package_obj = self.env['stock.quant.package']

        if not self.result_package_id:
            merged_package = package_obj.create({'location_id': self.dest_location_id.id, })
        elif self.result_package_id and self.dest_location_id:
            self.result_package_id.write({'location_id': self.dest_location_id.id})
            merged_package = self.result_package_id
        for line in line_ids:
            move_vals = {
                'name': (picking_id.name or '')[:2000],
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty_transfer,
                'quantity_done': line.qty_transfer,
                'product_uom': line.product_id.uom_id.id,


                'picking_id': picking_id.id,
                'location_id': line.source_location_id.id,
                'location_dest_id': self.dest_location_id.id,
            }
            move_obj.create(move_vals)
            move_objs = picking_id.move_ids.filtered(lambda m: m.product_id == line.product_id)
            move_objs._action_assign()

            for move in move_objs:
                move_line = move.move_line_ids.filtered(lambda ml: ml.product_id.id == move.product_id.id)
                move_line.write({
                    'package_id': line.package_id.id,
                    'result_package_id': merged_package.id,
                    'qty_done': line.qty_transfer,
                })
        picking_id.button_validate()

        return picking_id


class TransferPackageLine(models.TransientModel):
    _name = 'transfer.package.line'
    _description = 'Transfer Package Lines from Stock Quant.'

    transfer_package_id = fields.Many2one('transfer.package', string="Transfer")
    product_id = fields.Many2one('product.product', string="Product")
    quant_id = fields.Many2one('stock.quant', 'Stock Quant Id..')
    source_location_id = fields.Many2one('stock.location', 'Source Location')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    destination_location_id = fields.Many2one('stock.location', 'Destination Location')
    package_id = fields.Many2one('stock.quant.package', 'Source Package')
    result_package_id = fields.Many2one('stock.quant.package', 'Destination Package')
    qty_available = fields.Float(string="Onhand Quantity")
    qty_transfer = fields.Float(string="Qty To Transfer")
    company_id = fields.Many2one('res.company', 'Company')


    @api.onchange('destination_location_id')
    def onchange_destination_location_id(self):
        for line in self:
            if line.source_location_id == line.destination_location_id:
                raise UserError("Destination location should be different than Source location.")


