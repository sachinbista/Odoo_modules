import logging
from odoo import fields, models
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    abbreviated_description = fields.Text("Abbreviated Description")
