from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    available_warehouse_quantity_text = fields.Text(
        compute="_compute_available_warehouse_quantity",
        string="Availability"
    )

    @api.depends("product_id", "company_id")
    def _compute_available_warehouse_quantity(self):
        stock_quant_env = self.env['stock.quant'].sudo()
        stock_warehouse_env = self.env['stock.warehouse'].sudo()
        for rec in self:
            available_warehouse_quantity_text = ''
            product = rec.product_id
            if product:
                quants = stock_quant_env.search(
                    [
                        ("product_id", "=", product.id),
                        ("location_id.usage", "=", "internal"),
                        ("company_id", "=", rec.company_id.id)
                    ]
                )
                company_warehouse_locations = {}
                for quant in quants:
                    if quant.location_id not in company_warehouse_locations:
                        company_warehouse_locations.update({quant.location_id: 0})
                    company_warehouse_locations[quant.location_id] += quant.available_quantity
                company_warehouses = {}
                for location, quantity in company_warehouse_locations.items():
                    warehouse = location.warehouse_id
                    if warehouse.name not in company_warehouses:
                        company_warehouses.update({warehouse.name: 0})
                    company_warehouses[warehouse.name] += quantity
                for warehouse_name, quantity in company_warehouses.items():
                    if company_warehouses[warehouse_name] != 0:
                        available_warehouse_quantity_text = \
                            f"{available_warehouse_quantity_text} " \
                            f"{warehouse_name}: {quantity} <br/>"
            rec.available_warehouse_quantity_text = available_warehouse_quantity_text
