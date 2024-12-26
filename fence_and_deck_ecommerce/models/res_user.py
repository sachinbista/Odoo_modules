from odoo import models, api, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    aquirers_to_show = fields.Selection(related='partner_id.aquirers_to_show')
