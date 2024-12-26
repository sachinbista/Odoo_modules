import logging
from odoo import fields, models
_logger = logging.getLogger(__name__)


class MRPBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    abbreviated_description = fields.Text(
        "Abbreviated Description",
        related='product_id.abbreviated_description',
        readonly=False,
        store=True)
