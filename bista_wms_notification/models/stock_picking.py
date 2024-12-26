from odoo import api, fields, models, _
from odoo.addons.bista_wms_notification.push_notification import firebase_send_notification
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        if res.user_id and res.user_id.push_token:
            token = res.user_id.push_token
            data = {
                "title": "Transfer Created",
                "body": "New transfer created. Reference: %s" % res.name,
            }
            response = firebase_send_notification(self, token=token, data=data)
            if response and 'error' in response:
                _logger.exception("Error while sending notifications for transfer. Response: %s" % response)
            elif response:
                _logger.info("Notification send for transfer. Response: %s" % response)
        else:
            _logger.exception("user or user token not found while sending notification for transfer")
        return res

