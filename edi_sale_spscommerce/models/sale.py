import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    po_number = fields.Char(string='EDI PO Number',
                              help='Purchase order number from the EDI')
    

    @api.constrains('po_number')
    def set_po_related_fields(self):
        for rec in self:
            if not rec.client_order_ref:
                rec.client_order_ref = rec.po_number

    vendor = fields.Char(string='EDI Vendor Number')

    department = fields.Char(string='EDI Department Number')

    backorder_origin = fields.Many2one('sale.order',
                                         string='EDI Backorder Origin',
                                         help='Order from the EDI for with the current order is a backorder.')

    all_contacts = fields.Text(string='Contacts',
                                 help='Buyer and Receiving contacts transferred from the EDI')

    addresses = fields.Text(string='Addresses',
                              help='Delivery and Invoicing addresses transferred from the EDI')

    edi_status = fields.Selection(selection=[
                                ('draft', 'Draft'),
                                ('pending', 'Pending'),
                                ('sent', 'Sent'),
                                ('fail', 'Failed')
                                ], string='EDI Status', default='draft', copy=False)

    edi_date = fields.Datetime(string='EDI Document Date')

    tset_purpose_code = fields.Selection([
                        ('00', 'Original'),
                        ('06', 'Confirmation'),
                        ('NA', 'Unavailable')],
                        string='TSET Purpose Code',
                        help='Code identifying purpose or function of the transmission')

    primary_PO_type_code = fields.Selection([
                        ('SA', 'Stand Alone'),
                        ('NE', 'New Order'),
                        ('PR', 'Promotion Information'),
                        ('RO', 'Rush Order'),
                        ('CF', 'Confirmation'),
                        ('NA', 'Unavailable')],
                        string='Primary PO Type Code',
                        help='Code indicating the specific details regarding the ordering document')

    customer_payment_terms = fields.Text(string='Payment Terms')

    date_time_qualifier = fields.Char(string='Datetime Qualifier',
                                        help='Code specifying the type of date')

    requested_pickup_date = fields.Datetime(string='Requested Pickup Date', help='Date and time when date_time_qualifier equals 118')

    additional_date = fields.Datetime(string='Additional Date', help='Date and time when date_time_qualifier is neithor 002 nor 118')

    carrier_trans_method_code = fields.Selection(selection=[
                                ('A', 'Air'),
                                ('C', 'Consolidation'),
                                ('M', 'Motor[Common Carrier]'),
                                ('P', 'Private Carrier'),
                                ('BU', 'Bus'),
                                ('E', 'Expedited Truck'),
                                ('H', 'Customer Pickup'),
                                ('L', 'Contract Carrier'),
                                ('R', 'Rail'),
                                ('O', 'Containerized Ocean'),
                                ('T',  'Best Way[Shippers Option]'),
                            ], string='Carrier Trans Method', default='M')

    carrier_routing = fields.Char(string='Carrier Routing',
                                    help='Free-form description of the routing/requested routing for shipment or the originating carrier\'s identity')


    reference_qual = fields.Selection([
                        ('12', 'IA: Billing Account Number'),
                        ('AH', 'Agreement Number'),
                        ('IT', 'Internal Customer Number'),
                        ('CT', 'Contract Number'),
                        ('NA', 'Undefined')],
                        string='Reference Qualifier',
                        help='Code specifying the type of data in the ReferenceID/ReferenceDescription')

    reference_id = fields.Char(string='Reference ID',
                                 help='Value as defined by the ReferenceQual')

    description = fields.Char(string='Description',
                                help='Free-form textual description to clarify the related data elements and their content')

    note_code = fields.Selection([
                        ('GEN', 'ZZ: General Note'),
                        ('SHP', 'Shipping Note'),
                        ('NA', 'Undefined')],
                        string='Note Code',
                        help='Code specifying the type of note')

    charges_allowances = fields.Many2many('charge.allowance',
                                            string='Charges Allowances',
                                            help='Charges Allowances from EDI at Header and LineItem level.')




    total_line_item_number = fields.Integer(string='Total Line Item Number',
                             help='Sum of the total number of line items in this document')

    acknowledgement_type = fields.Selection([
                        ('AC', 'Acknowledge-With Detail and Change'),
                        ('AP', 'Acknowledge-Product Replenishment')],
                        default='AC',
                        string='Acknowledgement Type',
                        help='Code defining the vendor\'s status of the order as well as how much detail is being provided in the acknowledgement')

    bill_of_lading_number = fields.Char(string='Bill Of Lading Number', required=False, help='A shipper assigned number that outlines the ownership, terms of carriage and is a receipt of goods')


    def get_gross_selling_price(self, partner, product, package=None, inv_address=None):
        pricelist = self.env.ref('edi_sale_spscommerce.edi_pricelist')
        partner_products = pricelist.item_ids.filtered(lambda r: r.partner_id == partner and r.product_id == product)

        if package:
            pricelist_items = partner_products.filtered(lambda r: r.package_id == package)
        else:
            pricelist_items = partner_products.filtered(lambda r: not r.package_id)

        if len(pricelist_items) > 1:
            if not inv_address or inv_address == partner:
                pricelist_items = pricelist_items.filtered(lambda r: r.inv_partner_id == partner or \
                                                                     not r.inv_partner_id)
            else:
                pricelist_items = pricelist_items.filtered(lambda r: r.inv_partner_id == inv_address)

        if not pricelist_items:
            _logger.info('Price Not found for product %s and Barcode %s' % (product.name, product.barcode))
            return 0

        return pricelist_items.mapped('fixed_price')[0]



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    consumer_package_code = fields.Char(string='Consumer Package Code (EDI)',
                                          help='Consumer Package Code passed from the EDI. We store it because sometime it contains leading or training zeros that we need to transmit outbound. When searching for a product sometimes we need to strip these zeros to find the match.')

    line_sequence_number = fields.Char(string='Line Sequence Number',
                                         help='For an initiated document, this is a unique number for the line item[s]. For a return transaction, this number should be the same as what was received from the source transaction. Example: You received a Purchase Order with the first LineSequenceNumber of 10. You would then send back an Invoice with the first LineSequenceNumber of 10')

    buyer_part_number = fields.Char(string='Buyer Part Number',
                                      help='Buyer\'s primary product identifier')

    vendor_part_number = fields.Char(string='Vendor Part Number',
                                       help='Vendor\'s primary product identifier')

    part_number = fields.Char(string='Part Number',
                                help='Vendor\'s part number. Belongs to the <ProductID> field on the EDI file.')

    pack_size = fields.Float(string='Pack Size',
                               help='Measurable size of the sellable unit.')

    package_id = fields.Many2one('product.packaging', string='Package')

    price_unit = fields.Float(string='Gross Selling Price',
                              help='Price for specific case size for specific trading partner.')

    edi_price = fields.Float(string='EDI Price', digits='Product Price',
                                      help='Price passed from the EDI. If the order is in Cases and the price is in units, it will be converted to case price.')

    edi_unit_price = fields.Float(string='EDI Price (Units)',
                                    digits='Product Price',
                                    compute='_compute_unit_price',
                                    help='Unit Price passed from the EDI. If the EDI price was provided per case, this field divides it by the number of units contained in the case.')

    case_price = fields.Float(string='Selling Price (Cases)',
                                digits='Product Price',
                                compute='_compute_selling_price_cases',
                                help='Gross Selling Price in Cases')

    qty_cases = fields.Float(string='Quantity (Cases)',
                               compute='_compute_quantity_edi',
                               help='Quantity ordered in Cases. Change the UoM from Units to Cases if you want the case size to be taken into account in the computation.')

    charges_allowances = fields.Text(string='Charges Allowances',
                                       help='Charges Allowances from EDI at Header and LineItem level.')

    payment_terms = fields.Text(string='Payment Terms',
                                  help='Payment Terms from EDI at Header and LineItem level.')

    tax_code = fields.Selection(selection=[
                                    ('GS', 'Goods and Services[GST]'),
                                    ('ST', 'State/Provincial Sales'),
                                    ('TX', 'All Taxes'),
                                    ('BE', 'Harmonized Sales[HST]'),
                                    ('PG', 'state/Provincial Goods')
                                ], string='Tax Code',
                                help='For EDI purposes. Identification of the type of duty, tax, or fee applicable to \
                                commodities or of tax applicable to services.')

    tax_percent = fields.Float(string='Tax Percent',
                                 help='Tax percent passed from the EDI.')

    tax_id_edi = fields.Float(string='Tax ID EDI',
                            help='Tax ID from the EDI at line item level')

    item_status_code = fields.Selection(selection=[
                                    ('IA', 'Accept'),
                                    ('IB', 'Backordered'),
                                    ('IP', 'Accept - Price Changed'),
                                    ('IQ', 'Accept - Quantity Changed')
                                ], string='Item Status Code',
                                default='IA',
                                help='For EDI purposes. Code defining the vendor\'s status of the item.')

    @api.depends('edi_price', 'product_packaging_id', 'product_uom')
    def _compute_unit_price(self):
        for record in self:
            if record.product_packaging_id and record.product_uom.name == 'Cases' and record.product_packaging_id.qty:
                record['edi_unit_price'] = record.edi_price / record.product_packaging_id.qty
            else:
                record['edi_unit_price'] = record.edi_price

    @api.depends('product_uom_qty', 'product_packaging_id', 'product_uom')
    def _compute_quantity_edi(self):
        for record in self:
            if record.product_packaging_id and record.product_uom.name == 'Cases' and record.product_packaging_id.qty:
                record.qty_cases = record.product_uom_qty / record.product_packaging_id.qty
            else:
                record.qty_cases = record.product_uom_qty

    @api.depends('price_unit', 'order_id.partner_id', 'product_packaging_id', 'product_uom')
    def _compute_selling_price_cases(self):
        for record in self:
            if record.product_packaging_id and record.product_uom.name == 'Cases' and record.product_packaging_id.qty:
                record.case_price = record.price_unit * record.product_packaging_id.qty
            else:
                record.case_price = record.price_unit

    def _is_order_in_cases(self):
        """Returns True if the sale order line was ordered in cases instead of units."""

        return self.product_packaging_id and \
               self.product_packaging_id.qty and \
               self.product_uom.edi_code == 'CA'

    def compute_price_unit_and_case_price(self, pricelist_price):
        # If the order is in cases we need to adjust the prices
        if self._is_order_in_cases():
            if self.order_id.partner_id.price_in_cases:
                case_price = pricelist_price
                price_unit = pricelist_price / self.product_packaging_id.qty
            else:
                case_price = pricelist_price * self.product_packaging_id.qty
                price_unit = pricelist_price
        else:
            case_price = price_unit = pricelist_price

        return price_unit, case_price
