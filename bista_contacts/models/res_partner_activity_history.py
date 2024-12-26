# -*- encoding: utf-8 -*-

from odoo import models, _, api, fields

import logging

_logger = logging.getLogger(__name__)


class ResPartnerActivityHistory(models.Model):
    _name = 'res.partner.activity.history'
    _description = 'Partner Activity History'
    _rec_name = 'summary'

    source_document = fields.Char('Source Document Name')
    source_model = fields.Char('Source Model')
    source_record_id = fields.Integer('Source Record ID')
    summary = fields.Char('Summary')
    note = fields.Html('Note', sanitize_style=True)
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('Done', 'Done')], 'State')
    activity_type_id = fields.Many2one(
        'mail.activity.type', string='Activity Type')
    date = fields.Date('Date')
    date_deadline = fields.Date('Due Date')
    feedback = fields.Html('Feedback', sanitize_style=True)
    reference = fields.Char(
        'Source Document',
        compute='_compute_reference',
        readonly=True, store=True)

    @api.depends('source_model', 'source_record_id')
    def _compute_reference(self):
        for record in self:
            record.reference = "%s,%s" % (record.source_model, record.source_record_id)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    partner_activity_history_id = fields.Many2one('res.partner.activity.history', 'Activity History')

    def _action_done(self, feedback=False, attachment_ids=None):
        if self.partner_activity_history_id:
            self.partner_activity_history_id.write({
                'state': 'Done',
                'feedback': feedback,
            })
        return super(MailActivity, self)._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def action_close_dialog(self):
        super(MailActivity, self).action_close_dialog()
        ctx = dict(self.env.context) or {}
        res_id = ctx.get('default_res_id', False)
        model = ctx.get('default_res_model', False)
        if model and res_id:
            record_id = self.env[model].browse([res_id])
            try:
                if record_id.partner_id:
                    activity_history_id = self.env['res.partner.activity.history'].create({
                        'summary': self.summary,
                        'note': self.note,
                        'user_id': self.user_id.id,
                        'partner_id': record_id.partner_id.id,
                        'activity_type_id': self.activity_type_id.id,
                        'date_deadline': self.date_deadline,
                        'state': 'Draft',
                        'source_document': record_id.name,
                        'source_model': model,
                        'source_record_id': res_id
                    })
                    self.partner_activity_history_id = activity_history_id.id
            except Exception as ex:
                _logger.info(ex)
