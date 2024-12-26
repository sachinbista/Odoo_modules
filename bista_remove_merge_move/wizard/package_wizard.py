# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class PackageWizard(models.TransientModel):
    _name = 'package.wizard'
    _description = "Package Wizard"

    package_id = fields.Many2one('stock.quant.package', string='Package', domain="[('sale_order_id', '=', False),('customer_id', '=', False), ('quant_ids', '=', False)]")
    scan_barcode = fields.Char(string="Barcode")

    @api.onchange('scan_barcode')
    def onchange_scan_barcode(self):
        package = self.env['stock.quant.package']
        if self.scan_barcode:
            self.package_id = package.search(
                [('barcode', '=', self.scan_barcode)], limit=1)
            if self.package_id.sale_order_id:
                raise ValidationError("The selected package is already used on Sale Order %s." % self.package_id.sale_order_id.name)
                self.package_id = False

    def validate_package(self):
        """
        Function to link stock moves on the package on the pick confirmation.
        """
        picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
        moves = picking.move_ids

        if not self.package_id:
            raise UserError("Please select a package before validating.")

        for move in moves.move_line_ids:
            if not self.package_id.pack_date:
                self.package_id.write({
                    'sale_order_id': picking.sale_id.id,
                    'customer_id': picking.partner_id.id,
                    'location_id': picking.location_dest_id.id,
                    'pack_date': datetime.today()
                    })
            self.package_id.write({
                    'sale_order_id': picking.sale_id.id,
                    'customer_id': picking.partner_id.id,
                    'location_id': picking.location_dest_id.id,
                    })
            move.write({'result_package_id': self.package_id.id})
        return picking.with_context(package=True).button_validate()
