# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError
from bs4 import BeautifulSoup



class CalendarEventCrm(models.Model):
    _inherit = 'calendar.event'

    def _get_lead_values(self, partner):
        lead_value = super(CalendarEventCrm, self)._get_lead_values(partner)
        description = self.description
        if description:
            description_text = BeautifulSoup(description, "html.parser").get_text()
            lead_value.update({
                'trade_option': 'Trade In' if 'Trade Option' in description_text else False})
        return lead_value
