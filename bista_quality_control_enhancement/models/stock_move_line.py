# -*- encoding: utf-8 -*-
#
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#

from odoo import fields, models, api, _


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
   
    def write(self, vals):
        if 'qty_done' in vals:
            for rec in self:
                quality_check_domain = [
                ('move_line_id', '=', rec.id),
                ('product_id', '=', rec.product_id.id)
                ]
                if rec._create_quality_check_at_write(vals):
                    if rec.product_id.tracking == 'lot':
                        if rec.move_id.picking_type_id.use_create_lots:
                            quality_check_domain.append(('lot_name', '=', rec.lot_name))
                        else:
                            quality_check_domain.append(('lot_id', '=', rec.lot_id.id))
                    quality_check = self.env['quality.check'].search(quality_check_domain)
                    create_quality_check = vals.get('qty_done') - len(quality_check)
                    if create_quality_check > 0:
                        while(create_quality_check !=0):
                            create_quality_check-=1
                            self._create_check()
                    elif create_quality_check !=0:
                        while(create_quality_check !=0):
                            create_quality_check+=1
                            quality_check[0].sudo().unlink()
                            quality_check-=quality_check[0]
                elif vals.get('qty_done') == 0:
                    if rec.product_id.tracking == 'lot':
                        if rec.move_id.picking_type_id.use_create_lots:
                            quality_check_domain.append(('lot_name', '=', rec.lot_name))
                        else:
                            quality_check_domain.append(('lot_id', '=', rec.lot_id))
                    quality_check = self.env['quality.check'].search(quality_check_domain)
                    quality_check.sudo().unlink()
        return super(StockMoveLine, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(StockMoveLine, self).create(vals)
        if res.qty_done > 0 and res.product_id.tracking in ('lot','none'):
            quality_check_domain = [
            ('move_line_id', '=', res.id),
            ('product_id', '=', res.product_id.id)
            ]
            if res.product_id.tracking == 'lot':
                if res.move_id.picking_type_id.use_create_lots:
                    quality_check_domain.append(('lot_name', '=', res.lot_name))
                else:
                     quality_check_domain.append(('lot_id', '=', res.lot_id.id))
            quality_check = self.env['quality.check'].search(quality_check_domain)
            create_quality_check = res.qty_done - len(quality_check)
            if create_quality_check > 0:
                while(create_quality_check !=0):
                    create_quality_check-=1
                    res._create_check()
        return res

class StockMove(models.Model):
    _inherit = "stock.move"

    def write(self, vals):

        if 'quantity_done'in vals and vals.get('quantity_done') == 0 and self.product_id.tracking in ('lot', 'none'):
            quality_check = self.env['quality.check'].search(
                [('product_id', '=', self.product_id.id), ('picking_id', '=', self.picking_id.id)])
            quality_check.sudo().unlink()
        return super(StockMove, self).write(vals)
