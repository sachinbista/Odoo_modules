from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    set_finished_product_location = fields.Boolean(string='Set Finish Product Location', config_parameter='bista_mo_finished_location.set_finished_product_location')
