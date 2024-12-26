from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    customer_po_required = fields.Boolean(string='Customer PO Required')
