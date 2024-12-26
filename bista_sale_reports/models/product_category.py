# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    display_name = fields.Char(string='Display Name', automatic=True, compute='_compute_display_name', store=True)
    is_service = fields.Boolean("Is Service", default=False)
    sale_type = fields.Selection(
        [('sale', 'Sales'), ('parts', 'Parts'), ('repair', 'Repairs'), ('service', 'Services')], 'Sale Type')

    def update_sale_type(self):
        for record in self:
            if record.parent_id and record.parent_id.sale_type:
                record.write({'sale_type': record.parent_id.sale_type})
            if record.child_id and record.sale_type:
                for child in record.child_id:
                    child.write({'sale_type': record.sale_type})
            return True

    def write(self, vals):
        for record in self:
            sale_type = vals.get('sale_type', False) or record.sale_type
            parent_id = vals.get('parent_id', False) or (record.parent_id and record.parent_id.id or False)
            if parent_id:
                category = self.env['product.category'].browse(parent_id)
                if sale_type and category.sale_type and category.sale_type != sale_type:
                    vals.update({'sale_type': category.sale_type})
                if not sale_type and category.sale_type:
                    vals.update({'sale_type': category.sale_type})
        return super(ProductCategory, self).write(vals)
