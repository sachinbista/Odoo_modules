# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ready_date = fields.Date(string="Ready Date")
    cargo_date = fields.Date(string="Cargo Date")
    etd_date = fields.Date(string="ETD")
    eta_date = fields.Date(string="ETA")
    shipping_point_from = fields.Char(string="Shipping Point From")
    shipping_point_to = fields.Char(string="Shipping Point To")
    shipping_method = fields.Char(string="Shipping Method")
    shipping_window = fields.Date(string="Shipping Window")
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    def button_cancel(self):
        form_view_id = self.env.ref('purchase_extension.po_so_cancel_reason_wizard')
        if not self.env.context.get('fromwizard'):
            return {
                'name': 'Cancel Reason',
                'type': 'ir.actions.act_window',
                'res_model': 'cancel.reason.wizard',
                'view_mode': 'form',
                'view_id': form_view_id.id,
                'target': 'new',
                'context': {'default_purchase_order_id': self.id, 'caller': 'button_cancel'},
            }
        return super().button_cancel()

    @api.constrains('cargo_date','etd_date','eta_date')
    def _check_cargo_date(self):
        for rec in self:
            if rec.cargo_date and rec.ready_date and rec.cargo_date < rec.ready_date:
                raise ValidationError("Cargo Date should not be less than Ready Date.")
            elif rec.etd_date and rec.cargo_date and rec.etd_date < rec.cargo_date:
                raise ValidationError("ETD should not be less than Cargo Date.")
            elif rec.eta_date and rec.etd_date and rec.eta_date < rec.etd_date:
                raise ValidationError("ETA should not be less than ETD Date.")

