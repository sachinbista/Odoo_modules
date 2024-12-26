# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class SaleOrderCancel(models.TransientModel):
    _inherit = 'sale.order.cancel'

    def action_cancel(self):
        form_view_id = self.env.ref('purchase_extension.po_so_cancel_reason_wizard')
        if not self.env.context.get('salewizard'):
            sale = self.order_id
            sale_int = int(sale)
            return {
                'name': 'Cancel Reason',
                'type': 'ir.actions.act_window',
                'res_model': 'cancel.reason.wizard',
                'view_mode': 'form',
                'view_id': form_view_id.id,
                'target': 'new',
                'context': {'default_sale_order_id': sale_int,'wizard_id':self.id, 'caller': 'action_cancel'},
            }
        return super().action_cancel()
