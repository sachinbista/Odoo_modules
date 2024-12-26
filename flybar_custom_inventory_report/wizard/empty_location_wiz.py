from odoo import models, fields, api, _


class EmptyLocationWiz(models.TransientModel):
    _name = 'empty.location.wiz'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    warehouse_ids = fields.Many2many('stock.warehouse', 'sla_location_rel', 'sla_location_id', 'location_sla_id',  string="Warehouse")
    type = fields.Selection([('empty', 'Empty Location'),
                             ('partial_empty', 'Partial Empty Location')],string="Type", default='empty')
    view_type = fields.Selection([('storage_capacity', 'Storage Capacity'),
                                  ('location_dimension', 'Location Dimension')],
                                 string="View", default='location_dimension')
    def button_empty_location(self):
        if self.warehouse_id:
            location_ids = self.env['stock.location'].search([('warehouse_id', '=', self.warehouse_id.id),('usage', '=', 'internal'),('active', '=', True)])
            domain_location_lst = []
            parent_location_lst = []
            for location_id in location_ids:
                location_id.storage_capacity = location_id.stock_qty = location_id.stock_volume = location_id.stock_availability = location_id.total_case_count = location_id.total_pallet_count = 0.0

                if location_id.location_id.usage == 'internal' and location_id.location_id.id not in parent_location_lst:
                    parent_location_lst.append(location_id.location_id.id)

                if self.type == 'empty':
                    self.env.cr.execute("SELECT id FROM stock_quant WHERE location_id = %s" % location_id.id)
                    stock_quant_id = self.env.cr.fetchone()
                    if not stock_quant_id:
                        if self.view_type == 'storage_capacity':
                            storage_capacity = 0.0
                            for capacity in location_id.storage_category_id.product_capacity_ids:
                                storage_capacity += capacity.quantity
                            location_id.storage_capacity = storage_capacity
                        domain_location_lst.append(location_id.id)

                if self.type == 'partial_empty':
                    stock_qty = case_count = 0.0
                    pallet_count = 0
                    if location_id.storage_category_id and self.view_type == 'storage_capacity':
                        storage_capacity = 0.0
                        for capacity in location_id.storage_category_id.product_capacity_ids:
                            storage_capacity += capacity.quantity
                            self.env.cr.execute(f'SELECT sum(quantity - reserved_quantity) FROM stock_quant WHERE location_id = %s and product_id = %s',(location_id.id, capacity.product_id.id))
                            stock_quant_id = self.env.cr.fetchone()
                            if stock_quant_id[0]:
                                stock_qty += stock_quant_id[0]
                        if stock_qty > 0.0 and storage_capacity > stock_qty:
                            location_id.storage_capacity = storage_capacity
                            location_id.stock_availability = 100/storage_capacity*stock_qty
                            location_id.stock_qty = stock_qty
                            domain_location_lst.append(location_id.id)

                    if self.view_type == 'location_dimension':
                        availability = 0.0
                        self.env.cr.execute("SELECT id FROM stock_quant WHERE location_id = %s" % location_id.id)
                        stock_quant_ids = self.env.cr.fetchall()
                        for (stock_quant_id,) in stock_quant_ids:
                            browse_quant_id = self.env['stock.quant'].browse(stock_quant_id)
                            # if browse_quant_id.available_quantity > 0.0:
                            browse_product_id = self.env['product.product'].browse(browse_quant_id.product_id.id)
                            if browse_product_id.volume > 0.0:
                                stock_qty += browse_quant_id.available_quantity
                                if browse_quant_id.package_id and browse_quant_id.available_quantity > 0.0:
                                    pallet_count += 1
                                    # self.env.cr.execute("SELECT id FROM stock_move_line WHERE result_package_id = %s and product_id = %s and state = 'done'", (browse_quant_id.package_id.id, browse_product_id.id))
                                    move_line_id = self.env['stock.move.line'].search( [('result_package_id', '=', browse_quant_id.package_id.id), ('product_id', '=', browse_product_id.id),('state', '=', 'done'),('picking_id.picking_type_id.code', '=', 'internal')],limit=1)
                                    if move_line_id.product_packaging_id.qty > 0.0:
                                        case_count += browse_quant_id.available_quantity / move_line_id.product_packaging_id.qty
                            availability += browse_product_id.volume * browse_quant_id.available_quantity

                        if availability > 0.0 and location_id.volume > availability:
                            location_id.stock_volume = availability
                            location_id.stock_availability = 100 / location_id.volume * availability
                            location_id.stock_qty = stock_qty
                            location_id.total_pallet_count = pallet_count
                            location_id.total_case_count = case_count
                            domain_location_lst.append(location_id.id)

            if self.type == 'empty':
                for lst in parent_location_lst:
                    if lst in domain_location_lst:
                        domain_location_lst.remove(lst)

            # call Storage Location Analysis action
            action = self.env.ref("flybar_custom_inventory_report.action_report_storage_location_analysis")
            result = action.read()[0]
            # result['context'] = {'search_default_group_by_warehouse_id': True}
            result['domain'] = [('id', 'in', domain_location_lst)]
            return result