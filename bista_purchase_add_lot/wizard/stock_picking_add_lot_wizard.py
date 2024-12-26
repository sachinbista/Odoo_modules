from odoo import models, fields, api, _
from odoo import Command
from odoo.exceptions import UserError


class StockPickingAddLotWizard(models.TransientModel):
    _name = 'stock.picking.add.lot.wizard'
    _description = 'Stock Picking Add Lot Wizard'
    _inherit = ['barcodes.barcode_events_mixin']

    location_id = fields.Many2one('stock.location', string="To Location",
                                  domain="[('location_id', 'child_of', location_id)]")
    component_location_id = fields.Many2one('stock.location', string="Component Location")
    from_location_id = fields.Many2one('stock.location', string="From Location")
    barcode = fields.Char(string="Barcode")
    add_lot_ids = fields.One2many('stock.picking.add.lot.line.wizard', 'add_lot_id', string="Add lot")
    product_id = fields.Many2one('product.product', string="Product")
    picking_id = fields.Many2one('stock.picking')
    move_id = fields.Many2one('stock.move')
    qty_available = fields.Float(string="Quantity Available", compute='_compute_qty_available')

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        if self.qty_available > 0:
            if barcode:
                if not self.product_id:
                    product_ids = self.picking_id.move_ids_without_package.mapped('product_id').ids
                    domain = [('barcode', '=', barcode), ('id', 'in', product_ids)]
                    self.product_id = self.env['product.product'].search(domain, limit=1)
                    if self.product_id:
                        return

                if self.product_id:
                    self.barcode = barcode
                    existing_lot = self.env['stock.lot'].search([('name', '=', self.barcode)])
                    if existing_lot:
                        raise UserError(_("Lot/Serial Number '%s' already exists.") % self.barcode)

                    for line in self.add_lot_ids:
                        if line.lot_name == self.barcode:
                            raise UserError(_("Lot/Serial Number '%s' is already used in another line.") % self.barcode)

                    self.update({'add_lot_ids': [Command.create({'product_id': self.product_id.id,
                                                                 'location_id': self.location_id.id,
                                                                 'lot_name': barcode,
                                                                 'move_id': self.move_id.id,
                                                                 'prod_uom_id': self.move_id.product_uom,
                                                                 'location_from_id': self.component_location_id.id if self.component_location_id.id and self.product_id.bom_ids.type == 'subcontract' else self.from_location_id.id
                                                                 })]}
                                )
                else:
                    raise UserError(_("Please select the product first!"))
        else:
            raise UserError(_("No Quanity Available"))

    def submit_lot(self):
        for line in self.add_lot_ids:
            if self.qty_available < 0:
                raise UserError("Available Quantity cannot be in Negative")
            lot_id = self.env['stock.lot'].with_context(inventory_mode=True).create({
                'name': line.lot_name,
                'product_id': line.product_id.id,
                'company_id': self.env.company.id})
            values = {
                'product_id': line.product_id.id,
                'lot_id': lot_id.id,
                'lot_name': line.lot_name,
                'product_uom_id': line.prod_uom_id.id,
                'qty_done': line.qty_done,
                'picking_id': self.picking_id.id,
                'location_id': line.location_from_id.id,
                'move_id': line.move_id.id,
                'location_dest_id': self.location_id.id,
            }
            self.env['stock.move.line'].create(values)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            for move in self.picking_id.move_ids_without_package:
                if move.product_id.id == self.product_id.id:
                    self.move_id = move.id

    @api.depends('add_lot_ids.qty_done', 'move_id.product_uom_qty', 'move_id.quantity_done')
    def _compute_qty_available(self):
        for rec in self:
            done_qty_in_add_lot_ids = sum(
                rec.add_lot_ids.filtered(lambda lot: lot.product_id == rec.product_id).mapped('qty_done'))
            done_qty_in_stock_move = rec.move_id.quantity_done
            rec.qty_available = rec.move_id.product_uom_qty - done_qty_in_add_lot_ids - done_qty_in_stock_move
            if rec.qty_available < 0:
                raise UserError("Available Quantity cannot be in Negative")


class StockPickingAddLotLineWizard(models.TransientModel):
    _name = 'stock.picking.add.lot.line.wizard'
    _description = 'Stock Input Lot'

    add_lot_id = fields.Many2one('stock.picking.add.lot.wizard', string="Stock Input line")
    lot_name = fields.Char(string="Lot/Serial Number")
    location_id = fields.Many2one('stock.location', string="To Location")

    qty_done = fields.Float(string="Done")
    prod_uom_id = fields.Many2one('uom.uom', string="Unit of measure")
    product_id = fields.Many2one('product.product')
    move_id = fields.Many2one('stock.move')
    location_from_id = fields.Many2one('stock.location', string="From Location")
