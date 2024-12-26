from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    notify_user_ids = fields.Many2many('res.users',related='company_id.notify_user_ids', readonly=False)