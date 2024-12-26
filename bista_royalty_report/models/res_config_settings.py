from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    maximum_royalty_allowed = fields.Float('Maximum Royalty (%)',
                                           config_parameter='bista_royalty_report.maximum_royalty_allowed')
