##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from datetime import timedelta, date, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.service import common
from odoo.exceptions import MissingError, ValidationError, AccessError


class StockWarehousePoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    historical_days = fields.Integer('Historical Days')
    target_days = fields.Integer('Target Days')
    lead_days = fields.Integer('Lead Days')

    @api.constrains('historical_days', 'target_days', 'lead_days')
    def _check_stock_reordering_constrains(self):
        for rec in self:
            days = ''
            if rec.historical_days == 0:
                days += 'Historical Days' + ' ,'
            if rec.target_days == 0:
                days += 'Target Days' + ' ,'
            if rec.lead_days == 0:
                days += 'Lead Days'
            """
            Commented code as asked by Brandon.
            """
            # if days:
            #     raise ValidationError(_('The {} can not be zero'.format(days)))
            if rec.target_days < rec.lead_days:
                raise ValidationError(_('Target days can not be less than lead days.'))

    def cron_get_max_qty(self):
        self = self.search([])
        for rr in self:
            if rr.historical_days != 0 and rr.target_days:
                current_date = datetime.strftime(date.today(), DEFAULT_SERVER_DATE_FORMAT)
                past_date = datetime.strftime(date.today() - timedelta(days=rr.historical_days),
                                              DEFAULT_SERVER_DATE_FORMAT)
                sale_order_lines = self.env['sale.order.line'].sudo().search([
                    ('order_id.date_order', '>=', past_date + ' 00:00:00'),
                    ('order_id.date_order', '<=', current_date + ' 23:59:59'),
                    ('product_id', '=', rr.product_id.id),
                    ('warehouse_id.lot_stock_id', '=', rr.location_id.id),
                    ('order_id.state', 'in', ['done', 'sale'])
                ])
                total_quantity = 0.0
                location_id = False
                for line in sale_order_lines:
                    total_quantity += line.product_uom_qty
                    location_id = line.warehouse_id.lot_stock_id
                if location_id and rr.product_id:
                    stock_warehouse_order_point_id = self.env['stock.warehouse.orderpoint'].search(
                        [('location_id', '=', location_id.id), ('product_id', '=', rr.product_id.id)])
                    stock_warehouse_order_point_id.product_max_qty = total_quantity * rr.target_days / rr.historical_days
                    stock_warehouse_order_point_id.product_min_qty = total_quantity * rr.lead_days / rr.historical_days
