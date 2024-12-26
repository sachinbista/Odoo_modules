# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re
import logging
_logger = logging.getLogger(__name__)


class Edi856(models.Model):
    _name = 'spring.edi.856'
    _description = 'edi856'

    spring_system_so_id = fields.Char(string='Spring System SO ID')
    spring_system_vendor_num = fields.Char(string='Spring System vendor Num')
    spring_system_po_num = fields.Char(string='Spring System po num')
    spring_system_ship_id = fields.Char(string='Spring System Ship ID')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    config_id = fields.Many2one('spring.systems.configuration', string='EDI Config')
    edi_856_data = fields.Text('EDI File')
    system_errors = fields.Text('Errors')
    line_ids = fields.One2many('edi.856.lines', 'asn_id', string='Line Items', copy=True)
    notes = fields.Text('Notes')
    status = fields.Selection([('draft', 'Draft'), ('document', 'Document'), ('sent', 'Sent')], string='Status')
    shipping_label = fields.Binary('Shipping Label')
    shipping_slip = fields.Binary('Shipping Slip')

    # Dates
    ship_date = fields.Char('Ship Date')
    ship_time = fields.Char('Ship Time')

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    picking_id = fields.Many2one('stock.picking', string='Delivery Order')
    move_ids = fields.Many2many('stock.move', string='Moves')


class Edi856Lines(models.Model):
    _name = 'edi.856.lines'
    _description = 'edi856Lines'

    edi_po_no = fields.Char('PO No.')
    po_id = fields.Many2one('purchase.order', string="PO #")
    po_date = fields.Date('PO Date')

    isa_ref = fields.Char('ISA Reference')
    ship_stock_qty = fields.Float('Shipping Stock Qty')
    ship_purchase_qty = fields.Float('Shipped Purchase Qty')
    ship_uom = fields.Char('Shipped Purchase UOM')

    product_id = fields.Many2one('product.product', string='Product')

    line_error = fields.Boolean('Line Error')
    asn_id = fields.Many2one('spring.edi.856', string="ASN Number")
    status = fields.Selection([('draft', 'Draft'), ('sent', 'Sent')], string='Status')