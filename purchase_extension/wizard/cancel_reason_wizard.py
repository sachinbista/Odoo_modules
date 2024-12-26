# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class CancelReasonWizard(models.TransientModel):
    _name = 'cancel.reason.wizard'

    cancel_type = fields.Selection([('out_of_stock', 'Out Of Stock'), ('cost_issue', 'Cost Issue'),
                                    ('requested_by', 'Requested by vendor/customer'),('other','Other')],
                                    string='Cancel Type',required=True)
    reason_description = fields.Text(string="Description",required=True)

    cancel_type_label = fields.Char(string='Cancel Type Label', compute='_compute_cancel_type_label', readonly=True)

    @api.depends('cancel_type')
    def _compute_cancel_type_label(self):
        for record in self:
            record.cancel_type_label = dict(record._fields['cancel_type'].selection).get(record.cancel_type, '')


    def submit_cancel_reason(self):
        purchase_order_id = self.env.context.get('default_purchase_order_id')
        sale_order_id = self.env.context.get('default_sale_order_id')
        if purchase_order_id:
            purchase_order = self.env['purchase.order'].browse(purchase_order_id)
            if purchase_order:
                for line in purchase_order.order_line:
                    line.manually_received_qty_uom = line.qty_received
                html_code = f"<b>Cancel Type:</b> {self.cancel_type_label}<br/> <b>Cancellation Reason:</b> <i>{self.reason_description}</i>"
                purchase_order.message_post(body=html_code, subtype_xmlid="mail.mt_note")
                caller = self.env.context.get('caller')
                if caller == 'button_cancel':
                    purchase_order.with_context(fromwizard=True).button_cancel()

        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id)
            if sale_order:
                html_code = f"<b>Cancel Type:</b> {self.cancel_type_label}<br/> <b>Cancellation Reason:</b> <i>{self.reason_description}</i>"
                sale_order.message_post(body=html_code, subtype_xmlid="mail.mt_note")
                caller = self.env.context.get('caller')
                if caller == 'action_cancel':
                    wizard_id = self.env.context.get('wizard_id')
                    sale_cancel = self.env['sale.order.cancel'].browse(wizard_id)
                    sale_cancel.with_context(salewizard=True).action_cancel()
