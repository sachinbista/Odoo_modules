# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields


class AgentCommissionReports(models.Model):
    _name = 'agent.commission.reports'
    _description = 'Agent Commission Reports'

    invoice_date = fields.Date(string="Invoice Date")
    invoice_id = fields.Many2one('account.move',
                            string="Invoice Name")
    invoice_partner_id = fields.Many2one('res.partner',
                                string="Customer Name")
    gross_amount = fields.Float(string="Gross Amount")
    discount_amount = fields.Float(string="Discount Amount")
    freight_charges = fields.Float(string="Freight Charges")
    amazon_commission = fields.Float(string="Amazon Commission")
    net_sale = fields.Float(string="Net Sale")
    agent_id = fields.Many2one('res.partner', string="Agent")
    potential_commission_amt = fields.Float(string="Potential Commission Amt")
    potential_commission = fields.Float(string="Potential Commission")
    date_paid = fields.Date(string="Date Paid")
    amount_paid = fields.Float(string="Amount Paid")
    commissionable_amount = fields.Float("Commissionable Amount")
    commission = fields.Float(string="Commission")
    balance_commission = fields.Float(string="Balance Commission")

