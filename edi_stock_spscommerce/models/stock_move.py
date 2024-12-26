from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    consumer_package_code = fields.Char(string='Consumer Package Code (EDI)',
                              help='Consumer Package Code passed from the EDI. We store it because sometimes it contains leading or training zeros that we need to transmit outbound. When searching for a product sometimes we need to strip these zeros to find the match.')
    line_sequence_number = fields.Char(string='Line Sequence Number',
                              help='For an initiated document, this is a unique number for the line item[s]. For a return transaction, this number should be the same as what was received from the source transaction. Example: You received a Purchase Order with the first LineSequenceNumber of 10. You would then send back an Invoice with the first LineSequenceNumber of 10')
    buyer_part_number = fields.Char(string='Buyer Part Number',
                              help='Buyer\'s primary product identifier')
    vendor_part_number = fields.Char(string='Vendor Part Number',
                              help='Vendor\'s primary product identifier')
    part_number = fields.Char(string='Part Number',
                              help='Vendor\'s part number. Belongs to the <ProductID> field on the EDI file.')
    done_cases = fields.Float(string='Done Cases', compute='_compute_done_cases')
    ordered_cases = fields.Float(string='Ordered Cases', compute='_compute_ordered_cases')
    edi_uom = fields.Many2one(string='EDI UoM', comodel_name='uom.uom', copy=True)

    @api.depends('product_uom_qty')
    def _compute_done_cases(self):
        for record in self:
            if record.product_uom_qty and record.product_id and record.product_id.packaging_ids and record.product_id.packaging_ids[0].qty:
                record.done_cases = float(record.product_uom_qty / record.product_id.packaging_ids[0].qty)
            else:
                record.done_cases = record.product_uom_qty

    @api.depends('product_id.packaging_ids.qty')
    def _compute_ordered_cases(self):
        for record in self:
            if record.product_id.packaging_ids and record.product_id.packaging_ids[0].qty:
                record.ordered_cases = float(record.product_uom_qty / record.product_id.packaging_ids[0].qty)
            else:
                record.ordered_cases = 0


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'


    consumer_package_code = fields.Char(string='Consumer Package Code (EDI)',
                              help='Consumer Package Code passed from the EDI. We store it because sometimes it contains leading or training zeros that we need to transmit outbound. When searching for a product sometimes we need to strip these zeros to find the match.',
                              related='move_id.consumer_package_code')

    line_sequence_number = fields.Char(string='Line Sequence Number',
                              help='For an initiated document, this is a unique number for the line item[s]. For a return transaction, this number should be the same as what was received from the source transaction. Example: You received a Purchase Order with the first LineSequenceNumber of 10. You would then send back an Invoice with the first LineSequenceNumber of 10')
                              # related='move_id.line_sequence_number')

    buyer_part_number = fields.Char(string='Buyer Part Number',
                              help='Buyer\'s primary product identifier',
                              related='move_id.buyer_part_number')

    vendor_part_number = fields.Char(string='Vendor Part Number',
                              help='Vendor\'s primary product identifier',
                              related='move_id.vendor_part_number')

    part_number = fields.Char(string='Part Number',
                              help='Vendor\'s part number. Belongs to the <ProductID> field on the EDI file.',
                              related='move_id.part_number')

    done_cases = fields.Float(related='move_id.done_cases')
    ordered_cases = fields.Float(related='move_id.ordered_cases')
    edi_uom = fields.Many2one(comodel_name='uom.uom',
                                related='move_id.edi_uom')


    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if not record.line_sequence_number:
                existing_nums = self.picking_id.move_line_ids_without_package.sorted(
                    key=lambda r: int(r.line_sequence_number), reverse=True).mapped('line_sequence_number')
                num = str(int(existing_nums[0]) + 1) if existing_nums else '1'
                record.write({'line_sequence_number': num})
        return res
