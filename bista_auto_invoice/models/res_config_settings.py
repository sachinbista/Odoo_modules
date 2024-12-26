from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    chatter_group_id = fields.Many2one('mail.channel', related='company_id.chatter_group_id', readonly=False)
    enable_auto_invoice = fields.Boolean(readonly=False, related="company_id.enable_auto_invoice")