# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = ["sale.order", "commission.mixin"]
    _name = 'sale.order'

    @api.depends("agent_ids.amount")
    def _compute_commission_total(self):
        for record in self:
            record.commission_total = sum(record.mapped("agent_ids.amount"))

    @api.depends("order_line.price_subtotal")
    def _compute_discount_total(self):
        for record in self:
            record.discount_total = 0.0
            for line in record.order_line:
                record.discount_total += (line.price_unit * line.product_uom_qty) * line.discount / 100

    agent_ids = fields.One2many("sale.order.line.agent", 'object_id', string="Agents")

    commission_total = fields.Float(
        string="Agent Commission",
        compute="_compute_commission_total",
        store=True,
    )

    partner_agent_ids = fields.Many2many(
        string="Agents",
        comodel_name="res.partner",
        compute="_compute_agents",
        search="_search_agents",
    )

    discount_total = fields.Float(
        string="Discounts",
        compute="_compute_discount_total",
        store=True
    )

    @api.depends("partner_agent_ids", "agent_ids.agent_id")
    def _compute_agents(self):
        for so in self:
            so.partner_agent_ids = [
                (6, 0, so.mapped("agent_ids.agent_id").ids)
            ]

    @api.model
    def _search_agents(self, operator, value):
        sol_agents = self.env["sale.order.line.agent"].search(
            [("agent_id", operator, value)]
        )
        return [("id", "in", sol_agents.mapped("object_id.order_id").ids)]

    def recompute_lines_agents(self):
        self.mapped("order_line").recompute_agents()

    @api.depends("partner_id")
    def _compute_agent_ids(self):
        self.agent_ids = False  # for resetting previous agents
        for record in self:
            if record.partner_id:
                record.agent_ids = record._prepare_agents_vals_partner(
                    record.partner_id, settlement_type="sale_invoice"
                )


# class SaleOrderLine(models.Model):
#     _inherit = [
#         "sale.order.line",
#         "commission.mixin",
#     ]
#     _name = "sale.order.line"

#     # agent_ids = fields.One2many(comodel_name="sale.order.line.agent")

#     @api.depends("order_id.partner_id")
#     def _compute_agent_ids(self):
#         self.agent_ids = False  # for resetting previous agents
#         for record in self:
#             if record.order_id.partner_id and not record.commission_free:
#                 record.order_id.agent_ids = record.order_id._prepare_agents_vals_partner(
#                     record.order_id.partner_id, settlement_type="sale_invoice"
#                 )

#     # def _prepare_invoice_line(self, **optional_values):
#     #     vals = super()._prepare_invoice_line(**optional_values)
#     #     vals["agent_ids"] = [
#     #         (0, 0, {"agent_id": x.agent_id.id, "commission_id": x.commission_id.id})
#     #         for x in self.agent_ids
#     #     ]
#     #     return vals


class SaleOrderLineAgent(models.Model):
    _inherit = "commission.line.mixin"
    _name = "sale.order.line.agent"
    _description = "Agent detail of commission line in order lines"

    object_id = fields.Many2one(comodel_name="sale.order")

    @api.depends(
        "commission_id",
        "object_id.amount_untaxed",
        "object_id.amount_tax",
        "object_id.amount_total"
    )
    def _compute_amount(self):
        for agent_line in self:
            order_id = agent_line.object_id
            net_amount = order_id.amount_total

            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            amazon_commission_rate = float(IrConfigParameter.get_param("commission.amazon_commission") or 0.0)
            amazon_store = self.env['goflow.store'].search([('channel', 'ilike', 'amazon')])

            # Amazon Charges Calculation
            if order_id.goflow_store_id and order_id.goflow_store_id.id in amazon_store.ids:
                amazon_charge = net_amount * amazon_commission_rate / 100
                net_amount -= amazon_charge

            # Freight Charges calculations
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            freight_product = int(IrConfigParameter.get_param("bista_freight_charges.freight_product")) or False
            freight_charge_lines = order_id.order_line.filtered(
                lambda line: line.product_id.id == freight_product)
            if freight_charge_lines:
                freight_charges = sum(freight_charge_lines.mapped('price_subtotal')) or 0.0
                net_amount -= freight_charges

            # Calculation for the agent's commission sale orders.
            agent_line.amount = agent_line._get_commission_amount(agent_line.commission_id, net_amount)
