from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    state = fields.Selection(selection_add=[('bounced', 'Bounced')
                                            ], ondelete={'bounced': 'cascade'})
