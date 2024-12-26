# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    def open_split_sale_order_wizard(self):
        context = self._context.copy()
        view = self.sudo().env.ref('bista_sale_split.bista_sale_split_sale_order_wizard')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Split Wizard',
            'view_mode': 'form',
            'res_model': 'sale.split.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
                }