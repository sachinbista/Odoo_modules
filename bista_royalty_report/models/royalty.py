# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo.exceptions import ValidationError

from odoo import api, fields, models, _


class Royalty(models.Model):
    _name = "royalty"
    _description = "Royalty"

    name = fields.Char(string="Royalty Code")
    # Commented as not used for now in code.
    # royalty_type = fields.Selection(
    #     selection=[("direct_import", "Direct Import"), ("domestic", "Domestic"), ("amazon", "Amazon"),
    #                ("target", "Target"), ("general", "General")],
    #     string="Type",
    #     required=True,
    #     default="general",
    # )
    royalty_percentage = fields.Float(string="Royalty Percentage")
    # Commented as not used for now in code.
    # partner_id = fields.Many2one("res.partner", string="Royalty Agent", domain="[('is_royalty_agent', '=', True)]")
    active = fields.Boolean(default=True)

    @api.constrains('royalty_percentage')
    def _check_royalty_percentage_range(self):
        for royalty_line in self:
            if royalty_line.royalty_percentage < 1 or royalty_line.royalty_percentage > 100:
                raise ValidationError(_('Add Royalty Percentage (%) Between 0-100.'))
