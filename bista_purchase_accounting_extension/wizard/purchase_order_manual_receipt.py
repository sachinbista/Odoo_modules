# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import datetime


class PurchaseOrderManualReceipt(models.TransientModel):
    _inherit = 'purchase.order.manual.receipt.wizard'

    container_id = fields.Char(string="Container")
    inv_reference = fields.Char(string="Invoice/ Bil Reference")
    inv_date = fields.Date(string="Merchandise Date", default=fields.Date.context_today)

    def _prepare_picking(self):
        res = super(PurchaseOrderManualReceipt, self)._prepare_picking()
        res.update({
            'container_id': self.container_id or '',
            })  
        return res

    def button_confirm(self):
        if self.purchase_order_id and not self.purchase_order_id.picking_type_id.is_dropship and not self.container_id:
            raise ValidationError(_(
                'Please Enter Container Information Required For Merchandise/Container'
            ))
        for line in self.line_ids:
            total_qty = line.purchase_line_id.manually_received_qty_uom - line.purchase_line_id.product_qty
            if total_qty > 0 and line.product_uom_qty > total_qty:
                raise ValidationError(_(
                    'Product Qty should not be greater than Product Total Qty for this product %(product_name)s',
                    product_name=line.product_id.display_name
                ))

            line.with_context({'container_id': self.container_id}).create_entries()
        if self.container_id:
            # Filter pickings whose state is not in cancel,done state

            filtered_pickings = self.purchase_order_id.picking_ids.filtered(lambda picking: picking.state not in ('done', 'cancel'))
            # Map the 'container_id' from the filtered pickings
            picking_container = filtered_pickings.mapped('container_id')
            if self.container_id in picking_container:
                self.purchase_order_id.last_container_status = 'container_exist'
                self.purchase_order_id.last_container = self.container_id
                self.purchase_order_id._activity_schedule_with_view('mail.mail_activity_data_warning',
                                                                    user_id=self.env.uid,
                                                                    views_or_xmlid='bista_purchase_accounting_extension.exception_purchase_order_same_container',
                                                                    render_context={
                                                                        'purchase_order_id': self.purchase_order_id,
                                                                        'container_id': self.container_id,
                                                                    })
            else:
                self.purchase_order_id.last_container_status = 'new_container'
                self.purchase_order_id.last_container = self.container_id
                html_code = f"<b>Merchandise/Container:</b> {self.container_id}<br/>"
                self.purchase_order_id.message_post(body=html_code, subtype_xmlid="mail.mt_note")
        return super().button_confirm()

    # @api.constrains('inv_date')
    # def _check_merchendise_date(self):
    #     for rec in self:
    #         if rec.inv_date and rec.inv_date > datetime.date.today():
    #             raise ValidationError(" Merchandise Date should not be greater than Current Date.")

    
    def _create_picking(self):
        picking_id = super(PurchaseOrderManualReceipt, self)._create_picking()
        if picking_id and picking_id.container_id:
            picking_id._onchange_container_id()
            if picking_id.date_eta:
                picking_id.move_ids.update({
                    'date': picking_id.date_eta
                    })
        return picking_id