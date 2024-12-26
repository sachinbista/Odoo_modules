from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    outbound_edi_asn = fields.Boolean(string='Outbound 856 ASN',
                                        help='True if the contact sends outbound Advanced Shipping Notice to the EDI')
