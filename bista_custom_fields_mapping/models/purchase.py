# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import api, exceptions, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    cancel_done_picking = fields.Boolean(string='Cancel Done Delivery?', compute='check_cancel_done_picking')
    ownership = fields.Selection(string='Ownership', selection=[('owned', 'Owned'), ('memo', 'Memo')], default='owned',
                                 required=True)
    owner = fields.Many2one(comodel_name='res.partner', compute='get_owner', string='Owner')


    @api.model
    def check_cancel_done_picking(self):
        for order in self:
            Flag = False
            if order.company_id.cancel_done_picking and order.picking_count > 0:
                for picking in self.picking_ids:
                    if picking.state != 'cancel':
                        Flag = True
                        break
            order.cancel_done_picking = Flag

    def get_owner(self):
        for res in self:
            if res.picking_ids:
                for pick in res.picking_ids.filtered(lambda s: s.owner_id and s.picking_type_code == 'incoming'):
                    if pick.owner_id:
                        res.owner = pick.owner_id.id
                        break

                else:
                    res.owner = False
            else:
                res.owner = False

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_vendor_code = fields.Char(string='Vendor Code',compute='get_vendor_code')

    def get_vendor_code(self):
        for res in self:
            vendor_code = self.env['product.supplierinfo'].search([('product_tmpl_id', '=', res.product_id.product_tmpl_id.id)], limit=1)
            res.product_vendor_code = vendor_code[0].product_code