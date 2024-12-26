# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
import json
from odoo import models, api, fields, _
from lxml import etree


class StockMove(models.Model):
    _inherit = 'stock.move'

    def get_original_sale_line_ids(self):
        so_line = self.sale_line_id or self.mapped('move_dest_ids.sale_line_id')
        for line in so_line:
            return line

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super(StockMove, self).get_view(view_id=view_id, view_type=view_type, options=options)
        if self.user_has_groups('bista_reports.group_inventory_read_user'):
            doc = etree.fromstring(res['arch'])
            if view_type == 'form':
                for node in doc.xpath("//field"):
                    modifiers = json.loads(node.attrib.pop('modifiers', '{}'))
                    modifiers['readonly'] = True
                    node.set('modifiers', json.dumps(modifiers))
                for node in doc.xpath("//button"):
                    modifiers = json.loads(node.attrib.pop('modifiers', '{}'))
                    modifiers['invisible'] = True
                    node.set('modifiers', json.dumps(modifiers))
                for node in doc.xpath("//form"):
                    modifiers = json.loads(node.attrib.pop('modifiers', '{}'))
                    node.set('create', '0')
                    node.set('modifiers', json.dumps(modifiers))
                res['arch'] = etree.tostring(doc, encoding="unicode")
        return res

class QuantPackage(models.Model):
    """ Packages containing quants and/or other packages """
    _inherit = "stock.quant.package"

    quant_ids = fields.One2many('stock.quant', 'package_id', 'Bulk Content', readonly=False,
                                domain=['|', ('quantity', '!=', 0), ('reserved_quantity', '!=', 0)])

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    reserved_quantity = fields.Float(
        'Reserved Quantity',
        default=0.0,
        help='Quantity of reserved products in this quant, in the default unit of measure of the product',
        readonly=False, required=True, digits='Product Unit of Measure')