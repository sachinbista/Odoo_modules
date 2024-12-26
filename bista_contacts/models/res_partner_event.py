# -*- encoding: utf-8 -*-

from odoo import models, _, api, fields
from datetime import datetime
from odoo.exceptions import ValidationError

MONTHS = [
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
    ('December', 'December')
]

DAYS = [(str(i), str(i)) for i in range(1, 32)]

current_year = datetime.today().year
YEARS = sorted(
    [(str(current_year - i), str(current_year - i)) for i in range(125) if current_year - i >= 1900]
)


class ResPartnerRelation(models.Model):
    _name = 'res.partner.relation'
    _description = 'Partner Relation'

    name = fields.Char(string='Name')


class ResPartnerEvent(models.Model):
    _name = 'res.partner.event'
    _description = 'Partner Event'

    name = fields.Char(string='Name')


class ResPartnerEventDates(models.Model):
    _name = 'res.partner.event.dates'
    _description = 'Partner Event Dates'
    _rec_name = 'event_id'

    event_id = fields.Many2one('res.partner.event', string='Event')
    active = fields.Boolean('Active', default=True)
    month = fields.Selection(MONTHS, string='Month')
    day = fields.Selection(DAYS, string='Day')
    year = fields.Selection(YEARS, string='Year')
    other_event = fields.Char('Other Info')
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.model_create_multi
    def create(self, vals):
        events = super(ResPartnerEventDates, self).create(vals)
        for event in events:
            if event.event_id.name != 'Other':
                partner_events = self.search([
                    ('partner_id', '=', event.partner_id.id),
                    ('event_id', '=', event.event_id.id),
                    ('active', '=', True)])
                if partner_events and len(partner_events) > 1:
                    raise ValidationError("Multiple Events not allowed!")
        return events

    def write(self, values):
        result = super(ResPartnerEventDates, self).write(values)
        for event in self:
            if event.event_id.name != 'Other':
                partner_events = self.search([
                    ('partner_id', '=', event.partner_id.id),
                    ('event_id', '=', event.event_id.id),
                    ('active', '=', True)])
                if partner_events and len(partner_events) > 1:
                    raise ValidationError("Multiple Events not allowed!")
        return result
