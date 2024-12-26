# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    case_pack_qty = fields.Integer(string='Case Pack Qty')
    gtin_code = fields.Char(string='GTIN')
    package_type_barcode = fields.Char(related='product_packaging_id.barcode', string='Identifier')

    def button_add_note_control(self):
        view = self.env.ref('purchase_extension.add_dynamic_note_wiz_form_view')
        return {
            'name': _('To add a dynamic note'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'add.dynamic.note.wiz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_purchase_order_id=self.order_id.id if self.order_id else self._context.get('po_id')),
            }
