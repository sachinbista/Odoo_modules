import logging
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    transfer_sequence = fields.Integer(string='Transfer Sequence', default=10)
