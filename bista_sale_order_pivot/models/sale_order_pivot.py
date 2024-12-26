from odoo import fields, models, api


class SaleReport(models.Model):
    _inherit = 'sale.report'

    pattern_id = fields.Many2one('pattern', string="Pattern")
    color_name_id = fields.Many2one('color.name', string="Color Name")
    base_cloth_id = fields.Many2one('product.product', string="Base Cloth")
    fabric_content_id = fields.Many2one('fabric.content', string="Fabric Content")
    fabric_use_type = fields.Selection([('indoor', 'Indoor'),
                                        ('outdoor', 'Outdoor')], string="Fabric Use Type")
    uv_rating = fields.Integer(string="UV Rating")
    fabric_width = fields.Float(string="Fabric Width")
    fabric_weight = fields.Float(string="Fabric Weight")
    cleaning_code_id = fields.Many2one('cleaning.code', string="Cleaning Code")
    abrasion = fields.Integer(string="Abrasion")
    swatch_skus_id = fields.Many2one('product.product', string="Swatch SKUs")
    pattern_family_id = fields.Many2one('pattern.family', string="Pattern Family")
    color_family_id = fields.Many2one('color.family', string="Color Family")
    horizontal_repeat = fields.Float(string="Horizontal repeat")
    vertical_repeat = fields.Float(string="Vertical Repeat")
    prod_long_desc = fields.Text(string="Product Long Description")

    def _select_additional_fields(self):
        res = super(SaleReport, self)._select_additional_fields()
        res['pattern_id'] = "p.pattern_id"
        res['color_name_id'] = "p.color_name_id"
        res['base_cloth_id'] = "p.base_cloth_id"
        res['fabric_content_id'] = "p.fabric_content_id"
        res['fabric_use_type'] = "p.fabric_use_type"
        res['uv_rating'] = "p.uv_rating"
        res['fabric_width'] = "p.fabric_width"
        res['fabric_weight'] = "p.fabric_weight"
        res['cleaning_code_id'] = "p.cleaning_code_id"
        res['abrasion'] = "p.abrasion"
        res['swatch_skus_id'] = "p.swatch_skus_id"
        res['pattern_family_id'] = "p.pattern_family_id"
        res['color_family_id'] = "p.color_family_id"
        res['horizontal_repeat'] = "p.horizontal_repeat"
        res['vertical_repeat'] = "p.vertical_repeat"
        res['prod_long_desc'] = "p.prod_long_desc"

        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            p.pattern_id,
            p.color_name_id,
            p.base_cloth_id,
            p.fabric_content_id,
            p.fabric_use_type,
            p.uv_rating,
            p.fabric_width,
            p.fabric_weight,
            p.cleaning_code_id,
            p.swatch_skus_id,
            p.pattern_family_id,
            p.color_family_id,
            p.horizontal_repeat,
            p.vertical_repeat,
            p.prod_long_desc,
            p.abrasion"""

        return res
