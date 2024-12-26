from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    outbound_edi_inv = fields.Boolean(string='Outbound 810 Invoice',
                                        help='Whether the contact sends outbound 810 Invoices to the EDI.')
