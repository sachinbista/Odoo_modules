# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime
MONTH_SELECTION = [
        ('January', 'January'),
        ('February', 'February'),
        ('March', 'March'),
        ('April', 'April'),
        ('May', 'May'),
        ('June', 'June'),
        ('July', 'July'),
        ('August', 'August'),
        ('September', 'September'),
        ('October', 'October'),
        ('November', 'November'),
        ('December', 'December'),
    ]


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _description = 'Partner'

    birthday_day = fields.Integer('Birth Day')
    birthday_month = fields.Selection(MONTH_SELECTION, 'Birth Month', readonly= False)

    anniversary_day = fields.Integer('Anniversary Day', )
    anniversary_month = fields.Selection(MONTH_SELECTION, 'Anniversary Month')

    propose_day  = fields.Integer('Proposal Day')
    propose_month = fields.Selection(MONTH_SELECTION, 'Proposal Month')

    completion_perc = fields.Float(string='Card Completion %',compute='get_completion_perc')
    short_code = fields.Char('Short Code')

    def get_completion_perc(self):
        for res in self:
            perc = 0
            if res.street:
                perc += 10
            if res.city:
                perc += 10
            if res.zip:
                perc += 10
            if res.country_id:
                perc += 10
            if res.state_id:
                perc += 10
            if res.phone:
                perc += 10
            if res.mobile:
                perc += 10
            if res.email:
                perc += 10
            if res.birthday_month:
                perc += 5
            if res.anniversary_month:
                perc += 5
            if res.anniversary_day:
                perc += 5
            if res.birthday_day:
                perc += 5
            res.completion_perc = perc




