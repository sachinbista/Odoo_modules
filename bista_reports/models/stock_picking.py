# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
import json
from odoo import models, api, fields, _
import qrcode
import base64
from io import BytesIO
from lxml import etree


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    qr_code_pick = fields.Binary("QR Code Pick", attachment=True, compute='generate_qr_code')
    qr_code_out = fields.Binary("QR Code Out", attachment=True, compute='generate_qr_code')
    logo = fields.Binary('Shop Fabrick Img')
    is_printed = fields.Boolean('Is Printed',copy=False)
    is_inv_user = fields.Boolean('Is Inv User', compute='check_group')

    def get_service_type_product(self, line, taken_soln=[]):
        solines = self.env['sale.order.line']
        if self.sale_id and line:
            orig_sale_line_ids = line.get_original_sale_line_ids()
            if orig_sale_line_ids:
                for sol in self.sale_id.order_line:
                    if sol.id in taken_soln:
                        continue
                    if sol.visible_sequence > orig_sale_line_ids.visible_sequence:
                        if sol.display_type:
                            solines += sol
                        else:
                            break
            # for sol in self.sale_id.order_line:
            #     if (sol.id in taken_soln) or (sol in solines):
            #         continue
            #     if sol.sequence > orig_sale_line_ids.sequence:
            #         if not sol.product_id:
            #             solines += sol
            #         elif sol.product_id:
            #             break
            #
        solines -= solines.filtered(lambda l: l.is_delivery)
        return solines

    def check_group(self):
        if self.user_has_groups('bista_reports.group_inventory_read_user'):
            self.is_inv_user = True
        else:
            self.is_inv_user = False

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super(StockPicking, self).get_view(view_id=view_id, view_type=view_type, options=options)
        if self.user_has_groups('bista_reports.group_inventory_read_user'):
            doc = etree.fromstring(res['arch'])
            if view_type == 'form':
                for node in doc.xpath("//field"):
                    modifiers = json.loads(node.attrib.pop('modifiers', '{}'))
                    modifiers['readonly'] = True
                    node.set('modifiers', json.dumps(modifiers))
                for node in doc.xpath("//form"):
                    modifiers = json.loads(node.attrib.pop('modifiers', '{}'))
                    node.set('create', '0')
                    node.set('delete', '0')
                    node.set('modifiers', json.dumps(modifiers))
                res['arch'] = etree.tostring(doc, encoding="unicode")
        return res

    def mark_printed_true(self):
        self.is_printed = True

    @api.model_create_multi
    def create(self, vals_list):
        """Picking name must have PO or SO name in it."""
        for vals in vals_list:
            if origin := vals.get('origin', ''):
                so_obj = self.env['sale.order']
                if so := so_obj.search([('name', '=', origin)], limit=1):
                    if so.auto_generated and so.bs_inter_so_id:
                        company = so.bs_inter_so_id.company_id
                        vals.update({'logo': so.bs_inter_so_id.company_id.logo})
        return super(StockPicking, self).create(vals_list)

    def generate_qr_code(self):
        for rec in self:
            rec.qr_code_pick = ''
            rec.qr_code_out = ''
            if rec.sale_id:
                for picking in rec.sale_id.picking_ids:
                    if picking.picking_type_code == 'internal':
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(rec.name)
                        qr.make(fit=True)
                        img = qr.make_image()
                        temp = BytesIO()
                        img.save(temp, format="PNG")
                        qr_image = base64.b64encode(temp.getvalue())
                        rec.qr_code_pick = qr_image
                    if picking.picking_type_code == 'outgoing' and picking.state not in ['done', 'cancel']:
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(picking.name)
                        qr.make(fit=True)
                        img = qr.make_image()
                        temp = BytesIO()
                        img.save(temp, format="PNG")
                        qr_image = base64.b64encode(temp.getvalue())
                        rec.qr_code_out = qr_image


class StockMove(models.Model):
    _inherit = 'stock.move'

    def location_reserve_name(self):
        for line in self:
            if line.move_line_ids:
                move_line_record_ids = line.move_line_ids.filtered(lambda rec: rec.product_id.id == line.product_id.id).sorted(key=lambda x: x.id)
                if move_line_record_ids:
                    return move_line_record_ids[0].location_id.complete_name
            else:
                return line.location_id.complete_name
