##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _, Command


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if not val.get('subcontractor_id'):
                if val.get('product_id'):
                    product_rec = self.env['product.product'].browse(val.get('product_id'))
                    bom = self.env['mrp.bom'].search([('product_tmpl_id','=',product_rec.product_tmpl_id.id)],limit=1)
                    val.update({'bom_id':bom.id})
        res = super(MrpProduction, self).create(vals_list)
        res._onchange_location_dest()
        return res


    @api.onchange('location_dest_id', 'move_finished_ids', 'bom_id')
    def _onchange_location_dest(self):
        # super(MrpProduction, self)._onchange_location_dest()
        for rec in self:
            if rec.bom_id and rec.bom_id.location_dest_id and 'is_manually' not in self._context:
                rec.update({
                    'location_dest_id': rec.bom_id.location_dest_id.id or False
                    })

    def button_mark_done(self):
        if not self._context.get('from_manufacturing_order'):
            show_wizard = self.env['ir.config_parameter'].sudo().get_param('bista_mo_finished_location.set_finished_product_location')
            if show_wizard:
                if 'no_popup'not in self._context:
                    res = {}
                    production_location = []
                    change_production_location_id = self.env['change.production.location'].create({})
                    if change_production_location_id:
                        for mo in self:
                            self.env['change.production.location.line'].create(
                                {
                                    'mo_id': mo.id,
                                    'company_id': mo.company_id.id,
                                    'location_dest_id': mo.location_dest_id.id,
                                    'change_order_id': change_production_location_id.id,
                                    })
                        return {
                            'name': _('Change Production Location'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'change.production.location',
                            'view_id': self.env.ref('bista_mo_finished_location.view_change_production_location_wizard').id,
                            'type': 'ir.actions.act_window',
                            'res_id': change_production_location_id.id,
                            'target': "new"
                        }
        return super(MrpProduction, self).button_mark_done()

    @api.depends('company_id', 'bom_id')
    def _compute_picking_type_id(self):
        """
        Overidden base function to bypass odoo traceback coming on the create of MO
        """
        domain = [
            ('code', '=', 'mrp_operation'),
            ('warehouse_id.company_id', 'in', self.company_id.ids),
        ]
        picking_types = self.env['stock.picking.type'].search_read(domain, ['company_id'], limit=1)
        picking_type_by_company = {pt['company_id']: pt['id'] for pt in picking_types}
        default_picking_type_id = self._context.get('default_picking_type_id')
        default_picking_type = default_picking_type_id and self.env['stock.picking.type'].browse(default_picking_type_id)
        for mo in self:
            if default_picking_type and default_picking_type.company_id == mo.company_id:
                mo.picking_type_id = default_picking_type_id
                continue
            if mo.bom_id and mo.bom_id.picking_type_id:
                mo.picking_type_id = mo.bom_id.picking_type_id
                continue
            if mo.picking_type_id and mo.picking_type_id.company_id == mo.company_id:
                continue
            mo.picking_type_id = picking_type_by_company.get(mo.company_id.id, False)
