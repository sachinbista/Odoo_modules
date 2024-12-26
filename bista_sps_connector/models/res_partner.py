# -*- encoding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2024 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    edi_inbound_file_path = fields.Char(
        related='edi_config_id.edi_inbound_file_path', string="Inbound File Path", readonly=True)
    edi_outbound_file_path = fields.Char(
        related='edi_config_id.edi_outbound_file_path', string="Outbound File Path", readonly=True)
    edi_config_id = fields.Many2one('edi.config', string='EDI Config')
    edi_846 = fields.Boolean(string='EDI-846', readonly=False)
    edi_850 = fields.Boolean(string='EDI-850')
    edi_855 = fields.Boolean(string='EDI-855', readonly=False)
    edi_860 = fields.Boolean(string='EDI-860', readonly=False)
    edi_865 = fields.Boolean(string='EDI-865', readonly=False)
    edi_856 = fields.Boolean(string='EDI-856')
    edi_810 = fields.Boolean(string='EDI-810')
    edi_811 = fields.Boolean(string='EDI-811', readonly=False)
    edi_config_846 = fields.Boolean(
        related='edi_config_id.edi_846', string='EDI-846')
    edi_config_850 = fields.Boolean(
        related='edi_config_id.edi_850', string='EDI-850')
    edi_config_855 = fields.Boolean(
        related='edi_config_id.edi_855', string='EDI-855')
    edi_config_860 = fields.Boolean(
        related='edi_config_id.edi_860', string='EDI-860')
    edi_config_865 = fields.Boolean(
        related='edi_config_id.edi_865', string='EDI-865')
    edi_config_856 = fields.Boolean(
        related='edi_config_id.edi_856', string='EDI-856')
    edi_config_810 = fields.Boolean(
        related='edi_config_id.edi_810', string='EDI-810')
    edi_config_811 = fields.Boolean(
        related='edi_config_id.edi_811', string='EDI-811')
    trading_partner_id = fields.Char(string="Trading Partner ID")
    edi_contact_type = fields.Char(string="EDI Contact Type", readonly=True)
    edi_fax = fields.Char(string="EDI Fax")
    warehouse_id = fields.Many2one('stock.warehouse', copy=False, string="Warehouse")
    trading_partner_field_ids = fields.One2many('sps.trading.partner.fields', 'partner_id',
                                                string='Trading partner fields', widget='One2many_tags')

    # _sql_constraints = [
    #     ('trading_partner_id_unique', 'unique (trading_partner_id)', 'Enter unique trading partner ID!')]

    @api.model
    def _commercial_fields(self):
        """
        This function is used to restrict changing of the edi fields if the partner is a child of another partner.
        @author: Gauri Shenoy @Bista Solutions Pvt. Ltd.
        :return:
        """
        res = super(ResPartner, self)._commercial_fields()
        res += ['edi_inbound_file_path', 'edi_outbound_file_path', 'edi_config_id',
                'edi_846', 'edi_850', 'edi_855', 'edi_860', 'edi_865', 'edi_856', 'edi_810', 'edi_811',
                'edi_config_846', 'edi_config_850', 'edi_config_855', 'edi_config_860', 'edi_config_865',
                'edi_config_856', 'edi_config_810', 'edi_config_811', 'trading_partner_id']
        return res

    # @api.model
    # def create(self, vals):
    #     res = super(ResPartner, self).create(vals)
    #     partner_records = self.env['res.partner'].search([
    #         '|', ('id', '=', res.id), ('id', 'child_of', [res.id])
    #     ])
    #     if partner_records:
    #         res.update({'partner_ids': [(6, 0, partner_records.ids)]})
    #     return res

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        for rec in self:
            if vals.get('trading_partner_id'):
                partner_records = rec.search([
                    ('id', '!=', rec.id), ('id', 'child_of', [rec.id])
                ])
                for partner in partner_records:
                    partner.update({'trading_partner_id': vals.get('trading_partner_id')})
        return res
