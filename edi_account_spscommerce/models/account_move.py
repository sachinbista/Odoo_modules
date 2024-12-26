from odoo import fields, models, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    edi_status = fields.Selection(selection=[
                                    ('draft', 'Draft'),
                                    ('pending', 'Pending'),
                                    ('sent', 'Sent'),
                                    ('fail', 'Failed')
                                ], string='EDI Status', default='draft', copy=False)
    edi_date = fields.Datetime(string='EDI Document Date')

    quantity_totals_qualifier = fields.Selection(selection=[
                                    ('SQT', 'Summary Quantity Totals')
                                ], string='Quantity Totals Qualifier',
                                help='For EDI purposes. Qualifier used to define the related total amounts.')

    tset_purpose_code = fields.Selection([
                        ('00', 'Original'),
                        ('06', 'Confirmation'),
                        ('NA', 'Unavailable')],
                        string='TSET Purpose Code',
                        help='Code identifying purpose or function of the transmission')

    customer_payment_terms = fields.Text(string='Payment Terms')

    merch_type_code = fields.Char('Merchandise Type Code')

    def _check_edi_required_fields(self):
        """Checks that required fields are present before exporting invoice to EDI"""
        for invoice in self.filtered(lambda record: record.partner_id.outbound_edi_inv):
            if not invoice.merch_type_code:
                raise ValidationError('Merchandise Type Code is a required field for EDI.')

    def action_post(self):
        self._check_edi_required_fields()
        res = super().action_post()
        self.export_invoice_to_edi()
        return res


    def export_invoice_to_edi(self):
        base_edi = self.env['edi.sync.action']
        sync_action = base_edi.search([('doc_type_id.doc_code', '=', 'export_invoice_xml')], limit=1)
        if sync_action:
            invoices = self.filtered(lambda record: record.partner_id.outbound_edi_inv)
            invoices._check_edi_required_fields()
            base_edi._do_doc_sync_cron(sync_action_id=sync_action, records=invoices)

    @api.model_create_multi
    def create(self, vals_list):
        """Transfer EDI information from the origin sale order to the invoice"""

        res = super().create(vals_list)
        for record in res:
            if record.move_type == 'out_invoice' and record.invoice_origin:
                order = self.env['sale.order'].search([('name', '=', record.invoice_origin)], limit=1)
                if order:
                    record.tset_purpose_code = order and order.tset_purpose_code
                    record.customer_payment_terms = order and order.customer_payment_terms
                    for line in record.invoice_line_ids:
                        if line.sale_line_ids:
                            line.line_sequence_number = line.sale_line_ids[0].line_sequence_number
                            line.vendor_part_number = line.sale_line_ids[0].vendor_part_number
                            line.buyer_part_number = line.sale_line_ids[0].buyer_part_number
                            line.part_number = line.sale_line_ids[0].part_number
        return res
    



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Order Line
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

    qty_cases = fields.Float(string='Qty (Cases)', compute='_compute_qty_cases')

    case_price = fields.Float(string='Case Price', digits='Product Price', compute='_compute_case_price')

    product_uom_id = fields.Many2one(string='EDI UoM', comodel_name='uom.uom', copy=True, store=True)


    @api.depends('quantity')
    def _compute_qty_cases(self):
        for record in self:
            if record.quantity and record.product_id and record.product_id.packaging_ids and record.product_id.packaging_ids[0].qty:
                record['qty_cases'] = float(record.quantity / record.product_id.packaging_ids[0].qty)
            else:
                record['qty_cases'] = record.quantity

    @api.depends('price_unit', 'partner_id', 'product_id')
    def _compute_case_price(self):
        for record in self:
            if record.move_id.move_type == 'out_invoice':
                if record.partner_id.price_in_cases and record.product_id.packaging_ids and record.product_id.packaging_ids[0].qty and record.product_uom_id.edi_code == 'CA':
                    record['case_price'] = record.price_unit * record.product_id.packaging_ids[0].qty
                else:
                    record['case_price'] = record.price_unit
            else:
                record['case_price'] = 0

class AccountTax(models.Model):
    _inherit = 'account.tax'

    edi_taxcode = fields.Char(string='EDI Code', help='Two letter code that will identify the Tax Type on the EDI Invoice.\n \
                                                        BE: Harmonized Sales Tax (HST)\n \
                                                        GS: Goods and Services Tax (GST)')
