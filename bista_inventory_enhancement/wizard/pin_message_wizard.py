# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class PinMessageWizard(models.TransientModel):
    _name = "pin.message.wizard"
    _description = "Authentication Pin"

    manager_pin = fields.Char(string='Manager Pin', size=5)

    def decrypt(self, data = '5647e37eb98ddaebcd76c8f27364cdb0'):
            return "Decrypted: "+data
            del self.data
    def apply_manager_pin(self):
        context = dict(self.env.context or {})
        print("sdfdsfsd",context)
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
                    message = f"Manager Approval granted by {manager_user_obj.name} for this Inventory Adjustment : {active_inv_obj.name}"
                    active_inv_obj.message_post(body=message)
                    active_inv_obj.with_context({'approval_process': True}).action_validate()
        # message = ''
        # if not manager_user_obj:
        #     message += "Incorrect PIN\n"
        # if manager_user_obj and (active_so_obj.branch_id.id not in manager_user_obj.branch_ids.ids) if active_so_obj else False:
        #     message += "%s manager pin is not allowed for this branch.\n" %manager_user_obj.name

        # if message:
        #     raise UserError(_(message))
        # else:
        #     if context.get('active_model') == 'sale.order' and active_so_obj and 'check_cost' not in context:
        #         product_name = ''
        #         if active_so_obj.sale_part_id:
        #             product_name = active_so_obj.sale_part_id.with_context({'use_default_name': True}).name_get()[0][1]
        #             active_so_obj.write({
        #                 'permit_given_manager': manager_user_obj.id
        #             })
        #             active_so_obj.add_sale_lines()
        #         if context.get('sale_order_line_id'):
        #             line_ids = context.get('sale_order_line_id')
        #             line_ids = self.env['sale.order.line'].browse(line_ids)
        #             line_ids.write({
        #                 'return_rule_skiped': True
        #             })
        #             for line in line_ids:
        #                 product_name = line.product_id.with_context({'use_default_name': True}).name_get()[0][1]
        #                 if line.product_id.has_core:
        #                     line.write({
        #                         'return_rule_skiped': True
        #                     })
        #                 message = f"Manager Approval granted by {manager_user_obj.name} for this product : {product_name}"
        #                 active_so_obj.message_post(body=message)
        #     # active_so_obj.action_confirm()
        #     elif active_so_obj and 'check_cost' in context:
        #         if context.get('active_model') == 'sale.order':
        #             active_so_obj.with_context(from_sh_message_wizard=True).add_sale_lines()
        #         elif context.get('active_model') == 'repair.order':
        #             active_so_obj.with_context(from_sh_message_wizard=True).add_repair_lines()
                # message = f"Manager Approval granted by {manager_user_obj.name} for this product : {context.get('product_name')}"
                # active_so_obj.message_post(body=message)