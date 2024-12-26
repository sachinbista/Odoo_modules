# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    height = fields.Float(string="Height")
    width = fields.Float(string="Width")
    packaging_length = fields.Float(string="Length")

    length_uom_id = fields.Many2one(
        "uom.uom",
        string="Dimensions Units of Measure",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.uom_categ_length").id)
        ],
        help="UoM for packaging length, height, width (based on lenght UoM)",
        default=lambda self: self.env[
            "product.template"
        ]._get_length_uom_id_from_ir_config_parameter(),
    )
    length_uom_name = fields.Char(
        string="Length unit of measure label",
        related="length_uom_id.name",
        readonly=True,
    )

    weight = fields.Float(string="Weight")
    weight_uom_id = fields.Many2one(
        "uom.uom",
        string="Weight Units of Measure",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.product_uom_categ_kgm").id)
        ],
        help="Weight Unit of Measure",
        default=lambda self: self.env[
            "product.template"
        ]._get_weight_uom_id_from_ir_config_parameter(),
    )
    weight_uom_name = fields.Char(
        string="Weight unit of measure label",
        related="weight_uom_id.name",
        readonly=True,
    )

    volume = fields.Float(
        string="Volume",
        digits=(8, 4),
        store=False,
        help="The Packaging volume",
    )
    volume_uom_id = fields.Many2one(
        "uom.uom",
        string="Volume Units of Measure",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.product_uom_categ_vol").id)
        ],
        help="Packaging volume unit of measure",
        default=lambda self: self.env[
            "product.template"
        ]._get_volume_uom_id_from_ir_config_parameter(),
    )
    volume_uom_name = fields.Char(
        string="Volume Unit of Measure label",
        related="volume_uom_id.name",
        readonly=True,
    )

    # @api.depends(
    #     "packaging_length", "width", "height", "length_uom_id", "volume_uom_id"
    # )
    # def _compute_volume(self):
    #     for packaging in self:
    #         packaging.volume = packaging._calculate_volume(
    #             packaging.packaging_length,
    #             packaging.height,
    #             packaging.width,
    #             packaging.length_uom_id,
    #             packaging.volume_uom_id,
    #         )
    #
    # def _calculate_volume(
    #         self, packaging_length, height, width, length_uom_id, volume_uom_id
    # ):
    #     volume_m3 = 0
    #     if packaging_length and height and width and length_uom_id:
    #         length_m = self.convert_to_meters(packaging_length, length_uom_id)
    #         height_m = self.convert_to_meters(height, length_uom_id)
    #         width_m = self.convert_to_meters(width, length_uom_id)
    #         volume_m3 = length_m * height_m * width_m
    #     volume_in_volume_uom = self.convert_to_volume_uom(volume_m3,
    #                                                       volume_uom_id)
    #     return volume_in_volume_uom
    #
    # def convert_to_meters(self, measure, length_uom_id):
    #     uom_meters = self.env.ref("uom.product_uom_meter")
    #     return length_uom_id._compute_quantity(
    #         qty=measure,
    #         to_unit=uom_meters,
    #         round=False,
    #     )
    #
    # def convert_to_volume_uom(self, measure, volume_uom_id):
    #     uom_m3 = self.env.ref("uom.product_uom_cubic_meter")
    #     return uom_m3._compute_quantity(
    #         qty=measure,
    #         to_unit=volume_uom_id,
    #         round=False,
    #     )
