# -*- encoding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    height = fields.Float(string="Height")
    width = fields.Float(string="Width")
    length = fields.Float(string="Length")

    height_uom_id = fields.Many2one(
        "uom.uom",
        string="Height Unit of Measure",
        default=lambda self: self._get_height_uom_id_from_ir_config_parameter(),
    )
    width_uom_id = fields.Many2one(
        "uom.uom",
        string="Width Unit of Measure",
        default=lambda self: self._get_width_uom_id_from_ir_config_parameter(),
    )

    length_uom_id = fields.Many2one(
        "uom.uom",
        string="Length Unit of Measure",
        default=lambda self: self._get_length_uom_id_from_ir_config_parameter(),
    )

    @api.model
    def _get_height_uom_id_from_ir_config_parameter(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        default_uom = get_param("product_default_height_uom_id")
        if default_uom:
            return self.env["uom.uom"].browse(int(default_uom))

    @api.model
    def _get_width_uom_id_from_ir_config_parameter(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        default_uom = get_param("product_default_width_uom_id")
        if default_uom:
            return self.env["uom.uom"].browse(int(default_uom))

    @api.model
    def _get_length_uom_id_from_ir_config_parameter(self):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        default_uom = get_param("product_default_length_uom_id")
        if default_uom:
            return self.env["uom.uom"].browse(int(default_uom))
        else:
            return super()._get_length_uom_id_from_ir_config_parameter()
