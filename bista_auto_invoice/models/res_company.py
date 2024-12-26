from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    chatter_group_id = fields.Many2one(comodel_name="mail.channel")
    enable_auto_invoice = fields.Boolean()