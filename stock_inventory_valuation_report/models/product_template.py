# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def excute_type_product(self):
        product_template_ids = self.search([])
        product_template_ids._compute_type_product()

    @api.depends('detailed_type', 'categ_id', 'product_variant_ids', 'product_variant_ids.detailed_type', 'product_variant_ids.categ_id')
    def _compute_type_product(self):
        for product in self:
            type_product = 'other'
            
            if product.detailed_type in ('consu', 'product') and not product.categ_id:
                type_product = 'inventory'

            if product.detailed_type in ('consu', 'product') and product.categ_id:
                if 'Packaging' in product.categ_id.display_name:
                    type_product = 'packaging'

                if 'Replacement' in product.categ_id.display_name:
                    type_product = 'replacement_part'

                if not 'Packaging' in product.categ_id.display_name and not 'Replacement' in product.categ_id.display_name:
                    type_product = 'inventory'
                    

            product.write({'type_product' : type_product})
            product.product_variant_ids.write({'type_product' : type_product})

    type_product = fields.Selection([('inventory', "Inventory"),
                                     ('packaging', "Packaging"),  
                                     ('replacement_part', "Replacement Part"),
                                     ('other', "Other")], compute='_compute_type_product', store=True, string="Type")

class ProductProduct(models.Model):
    _inherit = "product.product"

    type_product = fields.Selection([('inventory', "Inventory"),
                                     ('packaging', "Packaging"),  
                                     ('replacement_part', "Replacement Part"),
                                     ('other', "Other")], string="Type")

