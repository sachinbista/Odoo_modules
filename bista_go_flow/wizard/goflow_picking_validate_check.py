from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime

class GoflowHoldOrderWiz(models.TransientModel):
    _name = "goflow.picking.validate.check"
    _description = "goflow.picking.validate.check"

    msg = fields.Char("Message")

