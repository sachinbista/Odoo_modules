from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    notify_user_ids = fields.Many2many('res.users')