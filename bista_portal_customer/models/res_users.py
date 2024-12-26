from odoo import models, fields

class ResUser(models.Model):
    _inherit = 'res.users'

    is_portal_customer = fields.Boolean("Portal Customer")
