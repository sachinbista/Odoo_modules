##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
import logging
from odoo import models, fields, api, _
import requests
import json
import traceback
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    shopify_fulfilled_qty = fields.Float("Fulfilled Qty", copy=False)
