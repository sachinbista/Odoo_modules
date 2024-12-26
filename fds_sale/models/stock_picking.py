import logging
from odoo import models, _, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        # Not allow to validate DO when OP is Committed Orders
        if self.picking_type_id == self.picking_type_id.warehouse_id.commit_type_id:
            raise ValidationError(_('You are not allowed to validate a Prelim Orders'))
        return super(StockPicking, self).button_validate()
