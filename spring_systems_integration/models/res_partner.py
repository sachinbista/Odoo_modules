# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    shipment_tracking = fields.Selection([
        ('auto', 'Auto'),
        ('manual', 'Manual')], default='manual', string='Shipment Tracking')
    is_edi_855 = fields.Boolean(string="Is EDI 855")