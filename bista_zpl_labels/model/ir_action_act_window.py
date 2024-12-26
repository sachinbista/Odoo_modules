from odoo import models, fields, api
from odoo.exceptions import UserError


class ActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(selection_add=[('zpl_view', 'ZPL View')], default="tree", ondelete={'zpl_view': 'set default'})
