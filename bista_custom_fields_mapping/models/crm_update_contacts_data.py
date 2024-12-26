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

class CrmUpdateContactsData(models.TransientModel):
    _name ='crm.update.contacts.data'
    _description = 'Update Contacts Data - CRM'

    def update_contacts_crm(self):
        contacts_missing_data = self.env['res.partner'].search([('email','=',False),('mobile','=',False),('street','=',False),('phone','=',False)])

        for res in contacts_missing_data:
            crm_data = self.env['crm.lead'].search([('partner_id','=',res.id),('email_from','!=',False) ,'|',('phone','!=',False),('mobile','!=',False),('street','!=',False)])

            if crm_data:
                for crm_data_res in crm_data:
                    if crm_data_res.email_from and not res.email:
                        res.email = crm_data_res.email_from

                    if crm_data_res.phone and not res.phone:
                        res.phone = crm_data_res.phone

                    if crm_data_res.mobile and not res.mobile:
                        res.mobile = crm_data_res.mobile

                    if crm_data_res.street and not res.street:
                        res.street = crm_data_res.street
                        res.zip = crm_data_res.zip
                        res.city = crm_data_res.city
                    logger.info('% s Has Been Updated' % res.name)

            # else:
            #     logger.info("% s Hasn't Been Updated" % res.name)
        return True