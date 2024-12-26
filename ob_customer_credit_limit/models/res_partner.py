# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_check = fields.Boolean('Active Credit', help='Activate the credit limit feature')

    # Todo: Remove Blocking field it is not longer used
    credit_blocking = fields.Monetary('Blocking Amount')
    credit_blocking_message = fields.Text()
    credit_blocking_threshold = fields.Monetary('Blocking Threshold',
                                                compute="_compute_credit_blocking_threshold",
                                                store=True)

    credit_warning = fields.Monetary('Warning Amount')
    credit_warning_message = fields.Text()
    credit_warning_threshold = fields.Monetary('Warning Threshold',
                                               compute="_compute_credit_warning_threshold",
                                               store=True)

    sale_order_line_ids = fields.One2many('sale.order.line',
                                          'partner_id',
                                          string='Sale Order Lines',
                                          domain=[('order_id.on_hold', '=', False),
                                                  ('order_id.state', 'not in', ['draft', 'cancel'])]
                                          )
    recalculate_credit_limit = fields.Boolean()

    def refresh_limit(self):
        self._recalculate_credit_limit(partner=self)

    @api.model
    def _recalculate_credit_limit(self, partner=None):
        partner_ids = partner or self.search([('recalculate_credit_limit', '=', True)])
        for partner in partner_ids:
            partner._compute_credit_threshold()
            partner.recalculate_credit_limit = False

    def _compute_onhold_status(self):
        for partner in self:
            sale_order = self.env['sale.order'].search([('partner_id', '=', partner.id),
                                                        ('state', 'not in', ['draft', 'cancel']),
                                                        ('on_hold', '=', True)])
            for sale in sale_order:
                sale_value = sum(line._get_to_invoice_value() for line in sale.order_line)
                if sale_value > partner.credit_blocking_threshold:
                    sale.on_hold = False
                    break

    def _compute_credit_threshold(self):
        self._compute_credit_warning_threshold()
        self._compute_credit_blocking_threshold()
        self._compute_onhold_status()

    @api.depends('sale_order_line_ids')
    def _compute_credit_blocking_threshold(self):
        for x in self:
            total_credit_sale = sum(line._get_to_invoice_value() for line in x.sale_order_line_ids)
            x.credit_blocking_threshold = x.credit_blocking - total_credit_sale if x.credit_blocking else 0

    @api.depends('sale_order_line_ids')
    def _compute_credit_warning_threshold(self):
        for x in self:
            total_credit_sale = sum(line._get_to_invoice_value() for line in x.sale_order_line_ids)
            x.credit_warning_threshold = x.credit_warning - total_credit_sale if x.credit_warning else 0

    @api.constrains('credit_warning')
    def _check_credit_amount(self):
        for credit in self:
            if credit.credit_warning < 0:
                raise ValidationError(_('Warning amount should not be less than zero.'))
