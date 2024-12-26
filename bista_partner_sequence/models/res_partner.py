# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (https://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_reference_no = fields.Char(string='Partner Reference', copy=False, required=True,
        readonly=False, default=lambda self: _('New'))

    @api.model
    def create(self, vals):
        if vals.get('partner_reference_no', _('New')) == _('New'):
            vals['partner_reference_no'] = self.env['ir.sequence'].next_by_code(
               'res.partner') or _('New')
            res = super(ResPartner, self).create(vals)
        return res

    def name_get(self):
        # if self._context.get('res_partner_sequence'):
        res = []
        for rec in self:
            if not self._context.get('commit_assetsbundle'):
                res.append((rec.id, '%s [%s]' % (rec.name, rec.partner_reference_no)))
            else:
                res.append((rec.id, '%s' % (rec.name)))
        return res
        # return super(ResPartner, self).name_get()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = list(args or [])
        if name:
            args += ['|',('partner_reference_no', operator, name),('name', operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
