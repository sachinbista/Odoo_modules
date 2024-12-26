##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields


class ShopifyRiskOrder(models.Model):
    _name = "shopify.risk.order"
    _description = 'Shopify Risk Order'

    name = fields.Char(string="Shopify Order Id", required=True)
    risk_id = fields.Char(string="Shopify Order Risk Id")
    cause_cancel = fields.Boolean(string="Cause Cancel")
    display = fields.Boolean(string="Display")
    message = fields.Text(string="Massage")
    score = fields.Float(string="Score")
    source = fields.Char(string="Source")
    order_id = fields.Many2one("sale.order", string="Order")
    recommendation = fields.Selection(
        [('cancel', 'This order should be cancelled by the merchant'),
         ('investigate',
          'This order might be fraudulent and needs further investigation'),
         ('accept', 'This check found no indication of fraud')
         ], string="Recommendation", default='accept')

    def create_risk_order_line_in_odoo(self, risk_dic, order):
        """
            This method used to create a fraud analysis line in order.
            @author: Pooja Zankhariya @Bista Solutions Pvt. Ltd.
        """
        is_risk_order = False
        if risk_dic.get('recommendation') != 'accept':
            is_risk_order = True
            vals = {'name': risk_dic.get('order_id'),
                    'risk_id': risk_dic.get('id'),
                    'display': risk_dic.get('display'),
                    'message': risk_dic.get('message'),
                    'score': risk_dic.get('score'),
                    'source': risk_dic.get('source'),
                    'cause_cancel': risk_dic.get('cause_cancel'),
                    'recommendation': risk_dic.get('recommendation'),
                    'order_id': order.id
                    }
            self.create(vals)
        return is_risk_order
