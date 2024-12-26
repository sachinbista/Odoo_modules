# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import UserError
import re



class BlockingWizard(models.TransientModel):
    _name = "blocking.wizard"
    _description = "Blocking Wizard"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)
    sale_id = fields.Many2one('sale.order', string="Sale Order")
    stock_picking_id = fields.Many2one("stock.picking")

    def action_confirm_order(self):

        self.sale_id.with_context(skip_warning=True).action_confirm()

        self.sale_id.update({
            'block_order':False,
            'flag':True,
        })

    def action_cancel(self):
        self.sale_id.update({
            'block_order': True,
        })


class WarningWizard(models.TransientModel):
    _name = "warning.wizard"
    _description = "Warning Wizard"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)
    sale_id = fields.Many2one('sale.order', string="Sale Order")
    stock_picking_id = fields.Many2one("stock.picking")


    def action_confirm(self):
        # if self.sale_id:
        #     self.sale_id.on_hold = True
        self.sale_id.with_context(skip_warning=True).action_confirm()

        # elif self.stock_picking_id:
        #     raise UserError("No group is allowed to perform this action")

class WarningWizardCustom(models.TransientModel):
    _name = "warning.wizard.custom"
    _description = "Warning Wizard Custom"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)
    sale_id = fields.Many2one('sale.order', string="Sale Order")

    def check_action(self):
        if self.sale_id:
            self.sale_id.update({'block_order':True})

class WizardBlock(models.TransientModel):
    _name = "wizard.block"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)

    def action_update_order_line(self):

        new_ids = tuple(map(int, re.findall(r'\d+', self.env.context.get("new_order_line_ids"))))

        # sale = self.env['sale.order'].browse(sale_id)

        for n_id in new_ids:

            res_id = self.env['getsale.orderdata'].search([('id','=',n_id)])
            # sale_id = self.env['sale.order'].browse(self._context.get('active_ids', []))


            order_line = self.env['sale.order.line'].search([('id','=',res_id.line_id.id)])
            if order_line:
                order_line.write({
                    'product_uom_qty': res_id.product_qty,
                    'price_unit': res_id.price_unit,
                })

    def action_wizard_close(self):
        return {'type': 'ir.actions.act_window_close'}

class WizardWarning(models.TransientModel):
    _name = "wizard.warning"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    name = fields.Text(string="Message", readonly=True, default=get_default)

    def action_update_order_line(self):

        new_ids = tuple(map(int, re.findall(r'\d+', self.env.context.get("new_order_line_ids"))))

        # sale = self.env['sale.order'].browse(sale_id)

        for n_id in new_ids:

            res_id = self.env['getsale.orderdata'].search([('id','=',n_id)])
            # sale_id = self.env['sale.order'].browse(self._context.get('active_ids', []))


            order_line = self.env['sale.order.line'].search([('id','=',res_id.line_id.id)])
            if order_line:
                order_line.write({
                    'product_uom_qty': res_id.product_qty,
                    'price_unit': res_id.price_unit,
                })

    def action_wizard_close(self):
        return {'type': 'ir.actions.act_window_close'}





