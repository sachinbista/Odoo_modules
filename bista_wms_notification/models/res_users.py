from odoo import api, fields, models, _


class ResUsers(models.Model):
    _inherit = "res.users"

    push_token = fields.Char('Push Notification Token', readonly=True)

