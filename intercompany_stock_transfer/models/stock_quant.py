# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import ValidationError


class StockQuants(models.Model):
    _inherit = 'stock.quant'

    def _generate_intra_inter_company_transfer(self):
        """
        This method will create Inter Company Stock Transfer record
        with fetching values from stock quants and its related record.
        """
        context = dict(self._context)
        location_ids = self.mapped('location_id')
        parent_location_ids = []
        for location in location_ids:
            if location.location_id.usage == 'internal':
                parent_location_id = location.location_id
            else:
                parent_location_id = location
            while parent_location_id.location_id.usage == 'internal':
                parent_location_id = parent_location_id.location_id
            parent_location_ids.append(parent_location_id)
        parent_location_ids = list(set(parent_location_ids))

        # Checking access rights of logged in users
        # If not enough access to create resupply transfer then warning message
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise ValidationError(_(
                "You don't have access to create resupply transfers. "
                "Please contact your administrator."))

        if len(parent_location_ids) > 1:
            raise ValidationError(
                _("Can not transfer lots from multiple locations at once !"))

        # Checking Warehouse is configured or not
        # If not warning
        warehouse = parent_location_ids[0].warehouse_id
        if not warehouse:
            raise ValidationError(
                _("No warehouse configured for selected Location !"))

        # Creating Inter-company record.
        inter_rec_line_ids = []
        for quant_rec in self:
            if quant_rec.quantity != quant_rec.available_quantity:
                raise ValidationError(_(
                    F"Product {quant_rec.product_id.display_name} is reserved in other transfer.\n"
                    F"On Hand Quantity: {quant_rec.quantity}\n"
                    F"Available Quantity: {quant_rec.available_quantity}"))
            inter_rec_line_ids.append((0, 0, {
                'name': quant_rec.product_id.partner_ref or '',
                'product_id': quant_rec.product_id.id,
                'product_uom': quant_rec.product_uom_id.id,
                'lot_id': quant_rec.lot_id and quant_rec.lot_id.id or False,
                'location_id': quant_rec.location_id.id,
                'product_uom_qty': quant_rec.quantity,
                'package_quant_id': quant_rec.package_id and quant_rec.package_id.id or False,
            }))
        wiz = self.env['inter.company.stock.transfer'].create({
            'transfer_type': 'inter_warehouse',
            'company_id': warehouse.company_id.id,
            'warehouse_id': warehouse.id,
            'line_ids': inter_rec_line_ids,
            'created_from_inv_report': True
        })
        # Returning form view of inter company record to open
        return {
            "view_type": "form",
            "view_mode": "form",
            "res_model": "inter.company.stock.transfer",
            "view_id": self.env.ref(
                "intercompany_stock_transfer.inter_company_stock_transfer_view"
                ).id,
            "type": "ir.actions.act_window",
            "context": context,
            "res_id": wiz.id,
        }
