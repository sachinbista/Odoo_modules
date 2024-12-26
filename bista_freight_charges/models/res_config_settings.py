from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    freight_product = fields.Many2one('product.product', 'Freight Product', domain="[('type', '=', 'service')]",
                                      config_parameter='bista_freight_charges.freight_product', )
