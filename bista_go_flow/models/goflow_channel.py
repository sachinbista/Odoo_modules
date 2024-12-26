# -*- coding: utf-8 -*-

from odoo import models, fields, api


class GoFlowChannel(models.Model):
    _name = 'goflow.channel'
    _description = 'GoFlow Channel'
    _rec_name = 'goflow_channel_name'

    partner_id = fields.Many2one('res.partner', string='Customer')
    # team_id = fields.Many2one('crm.team', string='Sales Team')
    goflow_channel_name = fields.Char(string='GoFlow Channel Name')
    goflow_store_name = fields.Char(string='GoFlow Store Name')
    goflow_store_id = fields.Text(string='GoFlow Store ID')

    import_orders = fields.Boolean(string='Import Orders', default=True)
    customer_to_company = fields.Boolean(string='Assign Customers to Company', default=True)
    allow_empty_address = fields.Boolean(string='Allow Empty Address')
    group_orders = fields.Boolean(string='Group Orders', default=True)
    use_channel_billing = fields.Boolean(string='Use Channel Billing')
    dsv_delivery_address = fields.Boolean(string='DSV Delivery Address')
    is_preferred_delivery_slip_readonly = fields.Boolean(string='Is Delivery Slip Readonly ')
    preferred_delivery_slip = fields.Selection([
        ('generated_delivery_slip', 'Generated Delivery Slip'),
        ('channel_delivery_slip', 'Channel Delivery Slip')], string='Preferred Delivery Slip')
    configuration_id = fields.Many2one('goflow.configuration', string='Instance')

    is_instance_invoice_matching = fields.Boolean(related="configuration_id.invoice_matching", string='Invoice Matching')
    invoice_matching = fields.Selection([
        ('match_only', 'Match Only'),
        ('set_remote_invoice_num', 'Set Remote Order ID'),
        ('set_odoo_invoice_num', 'Set Odoo Invoice Number on Remote Order')], string='Invoice Matching')
    update_sale_order_shipping_price = fields.Boolean(string='Update Sale Order Shipping Price')

    instance_manage_routing = fields.Boolean(related="configuration_id.manage_routing", string='Manage Routing - Instance')
    is_enable_routing = fields.Boolean(string='Enable Routing')
    routing_picking_type_ids = fields.Many2many('stock.picking.type', string='EDI Routing Operations')
