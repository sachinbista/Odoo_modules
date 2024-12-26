# -*- encoding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    product_default_weight_uom_id = fields.Many2one(
        "uom.uom",
        "Default Weight Unit of Measure",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.product_uom_categ_kgm").id)
        ],
        config_parameter="product_default_weight_uom_id",
        help="Default unit of measure to express product weight",
    )

    product_default_volume_uom_id = fields.Many2one(
        "uom.uom",
        "Default Volume Unit of Measure",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.product_uom_categ_vol").id)
        ],
        config_parameter="product_default_volume_uom_id",
        help="Default unit of measure to express product volume",
    )

    product_default_length_uom_id = fields.Many2one(
        "uom.uom",
        "Default Length Unit of Measure",
        domain=lambda self: [
            ("category_id", "=", self.env.ref("uom.uom_categ_length").id)
        ],
        config_parameter="product_default_length_uom_id",
        help="Default unit of measure to express product length",
    )
    product_default_width_uom_id = fields.Many2one(
        "uom.uom",
        "Default Width Unit of Measure",

        config_parameter="product_default_width_uom_id",
        help="Default unit of measure to express product length",
    )

    product_default_height_uom_id = fields.Many2one(
        "uom.uom",
        "Default Height Unit of Measure",
        config_parameter="product_default_height_uom_id",
        help="Default unit of measure to express product length",
    )


