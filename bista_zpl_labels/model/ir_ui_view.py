from odoo import models, fields, api
from odoo.exceptions import UserError


class View(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(selection_add=[('zpl_view', 'ZPL View')], default="tree", ondelete={'zpl_view': 'set default'})
