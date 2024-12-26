from odoo import _, api, fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    commit_type_id = fields.Many2one('stock.picking.type', 'Commit Type', check_company=True)

    @api.model
    def create_commit_type_for_warehouse(self):
        """ This hook is used to add commit type to exist warehouse when module is install.
        """
        warehouses = self.env['stock.warehouse'].with_context(active_test=False).search([])
        base_vals = {
           "name": "Preliminary Orders",
           "sequence": "1000",
           "code": "outgoing",
           "sequence_code": "COUT",
           "company_id": False,
           "warehouse_id": False,
           "default_location_src_id": False,
           "default_location_dest_id": self.env.ref('stock.stock_location_customers').id,
        }
        PickingType = self.env['stock.picking.type']
        for warehouse in warehouses:
            if not warehouse.commit_type_id:
                vals = base_vals.copy()
                vals.update({
                    "warehouse_id": warehouse.id,
                    "default_location_src_id": warehouse.lot_stock_id.id,
                    "company_id": warehouse.company_id.id
                })
                warehouse.commit_type_id = PickingType.create(vals)
