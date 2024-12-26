# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
#################################################################################

from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = "sale.order"


    @api.depends('order_line')
    def _compute_warranty_sale(self):

        for res in self:
            count = 0
            warranty = self.env['product.warranty'].search_count([('so_id','=',res.id)])
            res.update({'warranty_sale' :warranty})
            


    warranty_sale = fields.Integer(string="warranty",compute="_compute_warranty_sale")

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        create_warranty_with_saleorder = bool(self.env['ir.config_parameter'].sudo().get_param(
            "create_warranty_from_saleorder"))
        for line in self.order_line :
            if  create_warranty_with_saleorder == True and line.product_id.under_warranty == True:
                self.env['product.warranty'].create({
                    'partner_id' : self.partner_id.id,
                    'product_id' : line.product_id.id,
                    'phone' : self.partner_id.phone,
                    'email' : self.partner_id.email,
                    'so_id' : self.id,
                    'warranty_create_date': line.order_id.date_order or fields.date.today(),
                })


        return res
    
    def button_warranty(self):

        return{
        'name': _('warranty'),
            'view_mode': 'tree,form',
            'res_model': 'product.warranty',
            'view_id': False,
            'type': 'ir.actions.act_window',
           'domain': [('so_id', '=',self.id )],

        }
