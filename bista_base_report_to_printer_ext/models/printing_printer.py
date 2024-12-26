import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)

try:
    import cups
except ImportError:
    _logger.debug("Cannot `import cups`.")


class PrintingPrinter(models.Model):
    _inherit = "printing.printer"

    group_ids = fields.Many2many('res.groups')
    user_ids = fields.Many2many('res.users', compute="_compute_user_ids", store=True)

    @api.depends("group_ids.users")
    def _compute_user_ids(self):
        for x in self:
            user_ids = []
            for group in x.group_ids:
                user_ids += group.users.ids
            x.user_ids = [(6, 0, user_ids)]
