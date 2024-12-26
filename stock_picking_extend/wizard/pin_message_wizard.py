# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class QuantPinCheckWiz(models.TransientModel):
    _name = "quant.pin.check.wiz"
    _description = "Authentication Pin"

    manager_pin = fields.Char(string='Manager Pin', size=5)

    def decrypt(self, data = '5647e37eb98ddaebcd76c8f27364cdb0'):
            return "Decrypted: "+data
            del self.data
    def apply_manager_pin(self):
        context = dict(self.env.context or {})
        active_inv_obj, manager_user_obj = False, False
        if context.get('active_model') and context.get('active_id'):
            active_model = context.get('active_model')
            order_id = context.get('active_id')
            active_inv_obj = self.env[active_model].browse(int(order_id))
            manager_user_obj = self.env['res.users'].search([
                               ('pin_password', '=', self.manager_pin) 
                            ], limit=1)
            if not manager_user_obj and not context.get('from_barcode'):
                raise ValidationError("Please Enter Correct PIN")
            elif not manager_user_obj and context.get('from_barcode'):
                return 'Please Enter Correct PIN'
            else:
                if active_inv_obj:
                    if 'pin_for' in context and context.get('pin_for') == 'set_inventory':
                        active_inv_obj.with_context({'approval_process': True}).action_set_inventory_quantity()
                    if 'pin_for' in context and context.get('pin_for') == 'apply_inventory':
                        active_inv_obj.with_context({'approval_process': True}).action_apply_inventory()
                    if 'pin_for' in context and context.get('pin_for') == 'set_zero':
                        active_inv_obj.with_context({'approval_process': True}).action_set_inventory_quantity_to_zero()
                    if 'pin_for' in context and context.get('pin_for') == 'set_history':
                        active_inv_obj.with_context({'approval_process': True}).action_inventory_history()
                    if 'default_quant_ids' in context and 'default_show_info' in context:
                        active_inv_obj.with_context({'approval_process': True, 
                                                    'default_quant_ids': context.get('default_quant_ids'),
                                                    'default_show_info': context.get('default_show_info'),
                                                    }).action_apply()
                        
       