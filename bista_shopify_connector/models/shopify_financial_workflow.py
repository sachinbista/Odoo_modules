##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShopifyFinancialWorkflow(models.Model):
    _name = 'shopify.financial.workflow'
    _description = "Shopify Financial Workflow"

    name = fields.Char(string='Name', copy=False, index=True,
                       readonly=True, default=lambda self: _('New'))
    shopify_config_id = fields.Many2one('shopify.config', "Shopify Configuration",
                                        ondelete='cascade')
    company_id = fields.Many2one('res.company', related='shopify_config_id.default_company_id', string='Company', help='Company')
    auto_workflow_id = fields.Many2one("shopify.workflow.process",
                                       "Auto Workflow")
    payment_gateway_id = fields.Many2one("shopify.payment.gateway",
                                         "Payment Gateway")
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Terms')
    financial_status = fields.Selection([('any', 'Any'),
                                         ('authorized', 'Authorized'),
                                         ('pending', 'Pending'),
                                         ('unpaid', 'Unpaid'),
                                         ('paid', 'Paid'),
                                         ('partially_paid', 'Partially Paid'),
                                         ('refunded', 'Refunded'),
                                         ('partially_refunded', 'Partially '
                                                                'Refunded'),
                                         ('voided', 'Voided')],
                                        help="Shopify Financial Status.")

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('name', _('New')) == _('New'):
                val['name'] = self.env['ir.sequence'].next_by_code(
                    'shopify.financial.workflow') or _('New')
        return super().create(vals)

    @api.constrains('shopify_config_id', 'payment_gateway_id', 'financial_status')
    def _check_unique_financial_workflow(self):
        for fin_flow in self:
            domain = [('id', '!=', fin_flow.id),
                      ('shopify_config_id', '=', fin_flow.shopify_config_id.id),
                      ('payment_gateway_id', '=', fin_flow.payment_gateway_id.id),
                      ('financial_status', '=', fin_flow.financial_status)]
            if self.search(domain):
                raise ValidationError(_("You can't create duplicate Shopify "
                                        "Financial Workflow!"))
