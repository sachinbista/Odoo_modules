from odoo import fields, models

class Partner(models.Model):
    _inherit = 'res.partner'

    label_id = fields.Char(string='Label ID',
                             help='Identification number for the label template used by SPS Commerce API')
