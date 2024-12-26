# -*- coding: utf-8 -*-
from odoo import api, models, fields


class FiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    no_overwrite = fields.Boolean(
        help="If fiscal position is assigned to a warehouse and partner, "
             "This fields defines the priority for assigning a fiscal position to the sales order\n"
             "True: Do not overwrite partner fiscal period by warehouse fiscal period\n"
             "False: Replace with warehouse fiscal period if exists\n"
    )

