from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    can_commit_quotation = fields.Boolean('Can Preliminary Quotation?', default=False)
