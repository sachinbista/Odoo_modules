# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################
from odoo import models
import logging

logger = logging.getLogger(__name__)

class CleanUpContactsData(models.TransientModel):
    _name ='cleanup.contacts.data'
    _description = 'CleanUp Contacts Data'

    def cleanup_contacts_data(self):
        contacts_missing_data = self.env['res.partner'].search([('email','=',False),('mobile','=',False),('street','=',False),('phone','=',False)])
        for res in contacts_missing_data:
            if not self.has_business_with_us(res):
                logger.info('%s Has  Been Deleted' %res.name)
                res.sudo().unlink()

    def has_business_with_us(self,partner):
        crm_check = self.env['crm.lead'].search_count([('active','in',[True,False] ), ('partner_id','=',partner.id) ])
        sales_check = self.env['sale.order'].search_count([('partner_id','=',partner.id)])
        pos_check = self.env['pos.order'].search_count([('partner_id','=',partner.id)])
        invoices_check = self.env['account.move'].search_count([('partner_id','=',partner.id)])
        history_check = self.env['client.history'].search_count([('partner_id','=',partner.id)])
        purchase_order_check = self.env['purchase.order'].search_count([('partner_id','=',partner.id)])
        event_sponsor = self.env['event.sponsor'].search_count([('partner_id','=',partner.id)])
        res_users = self.env['res.users'].search_count([('active','in',[True,False] ), ('partner_id','=',partner.id)])

        if crm_check > 0 or sales_check > 0 or pos_check > 0 or invoices_check > 0 or history_check > 0 or purchase_order_check > 0 or event_sponsor > 0 or res_users > 0:
            return True
        else:
            return False

