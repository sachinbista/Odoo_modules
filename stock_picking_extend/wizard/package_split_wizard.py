# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PackageSplit(models.TransientModel):
    _name = 'package.split.wizard'

    product_name = fields.Char(string="Product Name")
    product_quantity = fields.Float(string="Product Quantity")
    quantity_for_packages = fields.Integer(string="Packaging Quantity")
    package_quantity = fields.Integer(string="# Of Packages",compute="_compute_package_quantity")


    def button_reset_put_in_pack(self):
        move_id = self.env['stock.move.line'].browse(self._context.get('active_ids'))
        picking_id = move_id.mapped("picking_id")
        product_id = move_id.move_id.product_id.id
        product_move_lines = picking_id.move_line_ids.filtered(lambda line: line.product_id.id == product_id)
        
        #calling goflow unpack box API
        # if picking_id.picking_type_id.code == 'outgoing':
        #     picking_id.goflow_unpack_box(product_move_lines)
        
        product_move_lines.unlink()
        picking_id.action_assign()

 
    @api.depends('product_quantity', 'quantity_for_packages')
    def _compute_package_quantity(self):
        for record in self:
            if record.product_quantity and record.quantity_for_packages:
                record.package_quantity = int(record.product_quantity / record.quantity_for_packages)
            else:
                record.package_quantity = 0

    def split_the_packages(self):
        move_id = self.env['stock.move.line'].browse(self._context.get('active_ids'))
        picking_id = move_id.mapped("picking_id")
        package_quantity = self.package_quantity
        for rec in range(package_quantity):
            if move_id.qty_done == 0:
                move_id.write({
                    'qty_done': self.quantity_for_packages,
                    'location_dest_id': picking_id.location_dest_id.id,
                })
                picking_id._put_in_pack(move_id)
            else:
                move_line_id = self.env['stock.move.line'].create({
                    'picking_id': picking_id.id,
                    'lot_id': move_id.move_id.lot_ids.id,
                    'qty_done': self.quantity_for_packages,
                    'product_id': move_id.move_id.product_id.id,
                    'product_uom_id': move_id.move_id.product_uom.id,
                    'location_dest_id': picking_id.location_dest_id.id,
                })
                picking_id._put_in_pack(move_line_id)

        # delivery picking
        # if picking_id.picking_type_id.code == 'outgoing':
        #     curr_product_move_lines = self.env['stock.move.line'].search([('picking_id','=',picking_id.id),('product_id','=',move_id.move_id.product_id.id)])
        #     picking_id.goflow_pack_box(curr_product_move_lines,move_id.move_id.product_id)



    def default_get(self, fields):
        res = super(PackageSplit, self).default_get(fields)
        product_name = self._context.get('product_name', False)
        product_quantity = self._context.get('product_quantity', False)
        if product_name:
            res['product_name'] = product_name
        if product_quantity:
            res['product_quantity'] = product_quantity

        return res
