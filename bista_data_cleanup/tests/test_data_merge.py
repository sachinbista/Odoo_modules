# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import common


class TestMergeFunctionality(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env['product.category'].create(
            {'name': 'All Products'}
        )

        cls.lot_sequence = cls.env['ir.sequence'].create({'name': 'Lot'}).id

        cls.group_a = cls.env['res.groups'].create({'name': 'Group A'})
        cls.group_b = cls.env['res.groups'].create({'name': 'Group B'})

        cls.inventory_admin = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'usera',
            'groups_id': [(6, 0, [cls.group_a.id, cls.env.ref('stock.group_stock_manager').id])]
        })

        cls.inventory_admin_b = cls.env['res.users'].create({
            'name': 'User B',
            'login': 'userb',
            'groups_id': [(6, 0, [cls.group_b.id, cls.env.ref('stock.group_stock_manager').id])]
        })

        cls.data_merge = cls.env['data_merge.group']

    def _create_product_and_move(self, tracking):
        product = self.env["product.product"].create(
            {'name': 'Test product',
             'type': 'product',
             'categ_id': self.category.id,
             'tracking': tracking or "none",
             'lot_sequence': self.lot_sequence
             })

        lot_production = self.env['stock.production.lot']

        lot_id = lot_production.create({
            'name': self._get_next_number('stock.production.lot'),
            'product_id': product.id,
            'company_id': self.env.company.id,
        })

        location = self.env['stock.location'].create({
            'name': f"Location {self._get_next_number('stock.location')}",
            'usage': 'internal',
            'active': True,
        })

        quant = self.env['stock.quant'].create({
            'product_id': product.id,
            'lot_id': lot_id.id if tracking else False,
            'location_id': location.id,
            'inventory_quantity': 1
        })

        lot_id_b = lot_production.create({
            'name': self._get_next_number('stock.production.lot'),
            'product_id': product.id,
            'company_id': self.env.company.id,
        })

        location_b = self.env['stock.location'].create({
            'name': f"Location {self._get_next_number('stock.location')}",
            'usage': 'internal',
            'active': True,

        })

        quant_b = self.env['stock.quant'].create({
            'product_id': product.id,
            'lot_id': lot_id_b.id if tracking else False,
            'location_id': location_b.id,
            'inventory_quantity': 1
        })

        quant.action_apply_inventory()
        quant_b.action_apply_inventory()
        return product

    def _get_next_number(self, model):
        return len(self.env[model].search([])) + 1

    def test_serialized_product_data_merge(self):
        product_a = self._create_product_and_move(tracking=False)
        product_b = self._create_product_and_move(tracking=False)
        self._merge(product_a, product_b)

    def _merge(self, master, to_merge):
        product_records = (master | to_merge)
        merge_data_action = self.env['data_merge.record'].action_deduplicates(product_records)
        merge_data = self.env['data_merge.record'].search(merge_data_action['domain'])
        merge_data.filtered(lambda x: x.res_id == master.id).write({'is_master': True})
        self.data_merge._merge_records(merge_data)


