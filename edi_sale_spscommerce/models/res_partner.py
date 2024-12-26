from odoo import fields, models


class Partner(models.Model):
    _inherit = 'res.partner'

    contact_type_code = fields.Selection([
                        ('BD', 'Buyer Name or Department'),
                        ('RE', 'Receiving Contact')],
                        string='Contact Type Code',
                        help='Code identifying a type of contact. For EDI use.')

    location_code_qualifier = fields.Selection([
                        ('UL', 'Global Location Number'),
                        ('9', 'Duns Plus 4 Number'),
                        ('92', 'Buyer Location Number'),
                        ('93', 'Code assigned by the organization originating the transaction set'),
                        ('1', 'Duns Number')],
                        string='Location Code Qualifier',
                        help='Code identifying the structure or format of the \
                        related location number[s]. For EDI use.')

    address_location_number = fields.Char(string='Address Location Number',
                                            help='Unique value assigned to identify a location. For EDI use.')

    inbound_edi_po = fields.Boolean(string='Inbound 850 PO',
                                      help='True if the contact receives inbound Sale Orders from the EDI.')

    price_in_cases = fields.Boolean(string='Price in Cases',
                                      help='True if the trading partner \
                                      sends the product price directly as case price \
                                      through the EDI 850, instead of unit price. \
                                      If False, the unit price will be multiplied by \
                                      the case size to populate the EDI Price field.')
