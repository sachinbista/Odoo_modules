from odoo import fields, models

class Partner(models.Model):
    _inherit = 'res.partner'

    inbound_edi_warehouse = fields.Boolean(string='Inbound 945 WSA',
                                             help='True if the contact receives Warehouse Shipping Advice from the EDI')
