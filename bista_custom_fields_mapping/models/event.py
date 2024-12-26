# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
#############################################################################

from odoo import models,fields,api
import datetime
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class EventEvent(models.Model):
    _inherit = 'event.event'

    day = fields.Char(string='Day', compute='compute_date')
    month = fields.Char(string='Month', compute='compute_date')
    year = fields.Char(string='Year', compute='compute_date')
    time = fields.Char(string='Time', compute='compute_date')
    day_of_week = fields.Char(string='Week Day', compute='compute_date')

    event_text_description = fields.Text(string='Event Description')
    event_img = fields.Binary('Logo File')

    facebook_link = fields.Char(string='Facebook Link')
    insta_link = fields.Char(string='Instagram Link')
    twitter_link = fields.Char(string='Twitter Link')

    def get_date_with_tz(self, date):
        datetime_with_tz = pytz.timezone(self._context['tz']).localize(fields.Datetime.from_string(date), is_dst=None)
        datetime_in_utc = datetime_with_tz.astimezone(pytz.utc)
        date = datetime_in_utc.strftime('%Y-%m-%d %H:%M:%S')
        return date

    # @api.multi
    def compute_date(self):
        for res in self:
            if res.date_begin:
                original_date = fields.Datetime.context_timestamp(self, datetime.datetime.strptime(str(res.date_begin),
                                                                                                   DEFAULT_SERVER_DATETIME_FORMAT))
                res.day_of_week = original_date.strftime("%a")
                res.day = original_date.day
                res.month = original_date.strftime("%b")
                res.year = original_date.year
                res.time = original_date.strftime("%I:%S %P")