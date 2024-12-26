# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _

class AddDynamicNoteWiz(models.TransientModel):
    _name = 'add.dynamic.note.wiz'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    add_dynamic_note_id = fields.Many2one('add.dynamic.note', string="Note Name")
    note = fields.Text(string="Description")

    @api.onchange('add_dynamic_note_id')
    def onchange_add_dynamic_note_id(self):
        if self.add_dynamic_note_id and self.add_dynamic_note_id.note:
            self.note = self.add_dynamic_note_id.note

    def action_validate(self):
        if self.purchase_order_id and self.add_dynamic_note_id and self.note:
            self.purchase_order_id.order_line.create({'name': self.note, 
                                                    'display_type': 'line_note', 
                                                    'order_id': self.purchase_order_id.id, 
                                                    'product_qty': 0.0,
                                                    'sequence': (max(self.purchase_order_id.order_line.mapped('sequence'))) + 1})
                                                    


    