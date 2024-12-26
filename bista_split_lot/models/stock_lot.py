# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _
from datetime import datetime
import pytz


class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model_create_multi
    def create(self, vals_list):
        lot_ids = super(StockLot, self).create(vals_list)
        for lot in lot_ids:
            product_id = lot.product_id
            if lot.product_id:
                if product_id.categ_id.auto_lot_generation:
                    tz = self._context.get('tz')
                    original_tz = pytz.timezone(tz)
                    original_dt = datetime.now().astimezone(original_tz)
                    lot_name = original_dt.strftime('%m-%d-%Y-%H-%M-%S')
                    existing_names = self.env['stock.lot'].search([('name', '=', lot_name)])

                    if existing_names:
                        suffix = 1
                        while True:
                            new_name = f"{lot_name}-{suffix}"
                            lot_with_suffix = self.env['stock.lot'].search([('name', '=', new_name)])
                            if not lot_with_suffix:
                                lot.name = new_name
                                break
                            suffix += 1
                    else:
                        lot.name = lot_name

        return lot_ids

    def name_get(self):
        if self._context.get('custom_split'):
            res = []
            for rec in self:
                if rec.product_qty > 0:
                    res.append((rec.id, '%s - %s' % (rec.name, rec.product_qty)))
            return res
        return super(StockLot, self).name_get()
