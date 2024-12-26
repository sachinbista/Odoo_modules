import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class RapaportAPIShape(models.Model):
    _name = 'rapaport.api.shape'
    _description = 'Rapaport API Shape'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)


class RapaportAPIColor(models.Model):
    _name = 'rapaport.api.color'
    _description = 'Rapaport API Color'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)


class RapaportAPIClarity(models.Model):
    _name = 'rapaport.api.clarity'
    _description = 'Rapaport API Clarity'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)