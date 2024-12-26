# Copyright 2021 VentorTech OU
# See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'printnode.mixin', 'printnode.scenario.mixin']

    location_id = fields.Many2one(
        'stock.location', "Source Location",
        compute="_compute_location_id", store=True, precompute=True,
        check_company=True, required=True)

    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        compute="_compute_location_id", store=True, precompute=True,
        check_company=True, required=True)

    def _put_in_pack(self, move_line_ids, create_package_level=True):
        package = super(StockPicking, self)._put_in_pack(move_line_ids, create_package_level)
        context = self.env.context.copy()  # Make a shallow copy to avoid modifying the original context
        if context.get('width') and context.get('length') and context.get('length'):
            package.write({
                'product_length': context.get('length'),
                'product_width': context.get('width'),
                'product_height': context.get('height')
            })
        if self.picking_type_id.is_auto_print_package and package:
            self.print_scenarios(action='print_package_on_put_in_pack_scenario_custom', packages_to_print=package)
        return package


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_auto_print_package = fields.Boolean(
        string="Auto Print Package",
        default=False,
        readonly=False)

class productTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('default_code')
    def check_internal_ref(self):
        if self.default_code:
            # Add your logic here based on what you want to check
            # For example, if internal_ref should be unique across records:
            duplicates = self.search([('default_code', '=', self.default_code)])
            if len(duplicates) > 1:
                raise UserError(_("The Internal Reference '%s' already exists.", self.default_code))
    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        domain = [('default_code', '=', self.default_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        # if self.env['product.template'].search(domain, limit=1):
        #     return {'warning': {
        #         'title': _("Note:"),
        #         'message': _("The Internal Reference '%s' already exists.", self.default_code),
        #     }}

class productTemplate(models.Model):
    _inherit = 'product.product'

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if not self.default_code:
            return

        domain = [('default_code', '=', self.default_code)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))

        # if self.env['product.product'].search(domain, limit=1):
        #     return {'warning': {
        #         'title': _("Note:"),
        #         'message': _("The Internal Reference '%s' already exists.", self.default_code),
        #     }}

    @api.constrains('default_code')
    def check_internal_ref(self):
        if self.default_code:
            # Add your logic here based on what you want to check
            # For example, if internal_ref should be unique across records:
            duplicates = self.search([('default_code', '=', self.default_code)])
            if len(duplicates) > 1:
                raise UserError(_("The Internal Reference '%s' already exists.", self.default_code))