# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo.exceptions import ValidationError

from odoo import models, fields, api, _


class ProductRoyaltyList(models.Model):
    _name = 'product.royalty.list'

    product_tmpl_id = fields.Many2one('product.template', 'Product Name')
    product_id = fields.Many2one('product.product', 'Variant Name')
    partner_id = fields.Many2one('res.partner', 'Agent', domain="[('is_royalty_agent','=', True)]")

    store_id = fields.Many2one('goflow.store', string="Store")

    royalty_rate = fields.Float('Royalty Rate')
    is_dropship = fields.Boolean("Is Dropship")

    royalty_id = fields.Many2one('royalty')
    royalty_type = fields.Selection(
        selection=[("direct_import", "Direct Import"), ("domestic", "Domestic"), ("amazon", "Amazon"),
                   ("target", "Target"), ("general", "General")],
        string="Type",
        required=True,
        default="general",
    )
    # Commented due to code change in royalty List
    # @api.constrains('royalty_rate')
    # def _check_range(self):
    #     for royalty_line in self:
    #         if royalty_line.royalty_rate < 1 or royalty_line.royalty_rate > 100:
    #             raise ValidationError(_('Add Royalty Rate (%) Between 0-100.'))

    @api.onchange('royalty_type')
    def _onchange_royalty_type(self):
        for royalty_line in self:
            if royalty_line.royalty_type == 'direct_import':
                self.is_dropship = True
            else:
                self.is_dropship = False

    @api.onchange('royalty_id')
    def _onchange_royalty_rate(self):
        for royalty_line in self:
            royalty_percent = 0.0
            if royalty_line.royalty_id:
                royalty_percent = royalty_line.royalty_id.royalty_percentage
            royalty_line.royalty_rate = royalty_percent
