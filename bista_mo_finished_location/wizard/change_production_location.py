# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import api, fields, models, _


class ChangeProductionLocation(models.TransientModel):
    _name = 'change.production.location'
    _description = 'Change Production Location'


    change_production_location_lines = fields.One2many(
        'change.production.location.line', 'change_order_id', 'To Change Finished Product Location')

    # def do_change_location(self):
    #     for production in self.change_production_location_lines:
    #         if production.mo_id.location_dest_id.id != production.location_dest_id.id:
    #             for move_finished_id in production.mo_id.move_finished_ids:
    #                 if  not production.mo_id.qty_producing:
    #                     production.mo_id.update({
    #                         'qty_producing': production.mo_id.product_qty
    #                         })
    #                     production.mo_id._set_qty_producing()
    #                 move_finished_id.update({
    #                     'location_dest_id': production.location_dest_id.id
    #                     })
    #         res = production.mo_id._pre_button_mark_done()
    #         if res is not True:
    #             return production.mo_id.with_context({'no_popup':True}).button_mark_done()
    #         production.mo_id.with_context({'no_popup':True}).button_mark_done()

    def do_change_location(self):
        for rec in self:
            for line in rec.change_production_location_lines:
                if line.mo_id.location_dest_id.id != line.location_dest_id.id:
                    for move_finished_id in line.mo_id.move_finished_ids:
                        if not line.mo_id.qty_producing:
                            line.mo_id.update({
                                'qty_producing': line.mo_id.product_qty
                            })
                            line.mo_id._set_qty_producing()
                        move_finished_id.update({
                            'location_dest_id': line.location_dest_id.id
                        })
                res = line.mo_id._pre_button_mark_done()
                if res is not True:
                    return line.mo_id.with_context({'no_popup': True}).button_mark_done()
                line.mo_id.with_context({'no_popup': True}).button_mark_done()


class ChangeProductionLocationLine(models.TransientModel):
    _name = 'change.production.location.line'

    change_order_id = fields.Many2one('change.production.location', string="Order Reference")
    mo_id = fields.Many2one('mrp.production', 'Manufacturing Order',
        required=True, ondelete='cascade')
    company_id = fields.Many2one(related='mo_id.company_id')
    location_dest_id = fields.Many2one(
        'stock.location', 'Finished Products Location',
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,tracking=True,
        help="Location where the system will stock the finished products.")
