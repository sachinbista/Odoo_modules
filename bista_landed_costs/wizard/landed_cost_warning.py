# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################


from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


class LandedCostWarningWizard(models.TransientModel):
    _name = 'landedcost.warning'

    description = fields.Text(string="Description",required=True)
    user_id = fields.Many2one("res.users", string="Assigned to?")

    def action_confirm(self):
        print("sfsdfsdfds",self._context)
        self.env['mail.activity'].sudo().create({
            'res_model_id': self.env.ref('stock.model_stock_picking').id,
            'res_id': self._context.get('pickingid'),
            'user_id': self.user_id.id,
            'summary': self.description,
        })

class LandedCostUnlinkWiz(models.TransientModel):
    _name = 'landedcost.unlink'

    landedcost_id = fields.Many2one('stock.landed.cost', "Landed Cost")
    landedcost_unlink_line = fields.One2many('landedcost.unlink.line', "landedcost_unlink_id", "Landed Cost Unlink Line")

    def action_validate(self):
        link_po_list = []
        unlink_po_list = []
        for line in self.landedcost_unlink_line:
            if not line.unlink_bool:
                link_po_list.append(line.purchase_order_id.id)
            if line.unlink_bool:
                unlink_po_list.append(line.purchase_order_id.name)
        if link_po_list:
            self.landedcost_id.po_ids = [(6, 0, link_po_list)]
        if unlink_po_list:
            body = _('Unlink Purchase orders:' + ', '.join(map(str, unlink_po_list)) )
            self.landedcost_id.message_post(body=body)
        

class LandedCostUnlinLinekWiz(models.TransientModel):
    _name = 'landedcost.unlink.line'

    landedcost_unlink_id = fields.Many2one('landedcost.unlink', "Landed Cost Unlink ID")
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    unlink_bool = fields.Boolean(string='Unlink')
        
        

    
